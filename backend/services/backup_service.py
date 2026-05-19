"""
Backup automático do banco SQLite para o storage (S3 ou local).
"""
import shutil
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Caminho padrão do banco — ajustável via variável de ambiente
DB_PATH = os.environ.get(
    "CONTROLLO_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "controllo.db"),
)


class BackupService:
    def __init__(self, storage=None):
        self._storage = storage

    def executar_backup(self) -> dict:
        """
        Copia o arquivo .db para o storage com timestamp.
        Retorna dict com status, nome do backup e tamanho.
        """
        db_path = os.path.abspath(DB_PATH)
        if not os.path.isfile(db_path):
            return {"sucesso": False, "erro": "Arquivo de banco não encontrado."}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_controllo_{timestamp}.db"

        # Copia para /tmp primeiro (snapshot consistente)
        tmp_dir = os.environ.get("TEMP", "/tmp")
        backup_path = os.path.join(tmp_dir, backup_name)

        try:
            shutil.copy2(db_path, backup_path)
        except Exception as e:
            logger.error("Falha ao copiar banco para tmp: %s", e)
            return {"sucesso": False, "erro": str(e)}

        tamanho_bytes = os.path.getsize(backup_path)

        # Upload para storage (S3 ou FileSystem)
        if self._storage:
            try:
                with open(backup_path, "rb") as f:
                    self._storage.save(f.read(), f"backups/{backup_name}")
                logger.info("Backup salvo no storage: backups/%s", backup_name)
            except Exception as e:
                logger.error("Falha ao enviar backup para storage: %s", e)
                return {
                    "sucesso": False,
                    "erro": f"Backup local OK, mas falha no storage: {e}",
                    "backup_local": backup_path,
                }
            finally:
                # Remove cópia temporária
                try:
                    os.remove(backup_path)
                except OSError:
                    pass

            # Limpar backups antigos
            self._limpar_backups_antigos(manter=30)
        else:
            logger.info("Storage não configurado — backup salvo em: %s", backup_path)

        return {
            "sucesso": True,
            "nome": backup_name,
            "tamanho_bytes": tamanho_bytes,
            "tamanho_mb": round(tamanho_bytes / (1024 * 1024), 2),
        }

    def _limpar_backups_antigos(self, manter: int = 30):
        """Mantém apenas os últimos N backups no storage."""
        if not self._storage:
            return
        try:
            arquivos = self._storage.list("backups/")
            if not arquivos:
                return
            # Ordena por nome (timestamp no nome garante ordem cronológica)
            backups = sorted(
                [a for a in arquivos if a.startswith("backups/backup_controllo_")],
            )
            excluir = backups[:-manter] if len(backups) > manter else []
            for arq in excluir:
                self._storage.delete(arq)
                logger.info("Backup antigo removido: %s", arq)
        except Exception as e:
            logger.warning("Erro ao limpar backups antigos: %s", e)
