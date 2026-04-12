/**
 * Validação de força de senha — espelhamento das regras do backend (R1).
 *
 * IMPORTANTE: o backend é a fonte de verdade. Esta validação é apenas UX
 * para feedback em tempo real. A regra 6 (zxcvbn/entropia) NÃO é verificada
 * no client para evitar bundle pesado (~400 KB). Se o backend rejeitar via
 * zxcvbn, o erro 422 é exibido normalmente.
 *
 * Regras determinísticas (1–5 + 7):
 *   1. Mínimo 8 caracteres
 *   2. Pelo menos 1 maiúscula ASCII (A-Z)
 *   3. Pelo menos 1 minúscula ASCII (a-z)
 *   4. Pelo menos 1 dígito
 *   5. Pelo menos 1 caractere especial: !@#$%^&*()_+-=[]{}|;:,.<>?
 *   7. Não conter o nome do usuário (case-insensitive)
 */

export interface RegrasSenha {
  minLength: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
  noUsername: boolean;
}

const ESPECIAIS = new Set("!@#$%^&*()_+-=[]{}|;:,.<>?".split(""));

export function validarSenha(
  senha: string,
  nomeUsuario: string = ""
): RegrasSenha {
  return {
    minLength: senha.length >= 8,
    uppercase: /[A-Z]/.test(senha),
    lowercase: /[a-z]/.test(senha),
    digit: /\d/.test(senha),
    special: [...senha].some((c) => ESPECIAIS.has(c)),
    noUsername:
      !nomeUsuario || !senha.toLowerCase().includes(nomeUsuario.toLowerCase()),
  };
}

export function senhaValida(regras: RegrasSenha): boolean {
  return Object.values(regras).every(Boolean);
}

export const REGRAS_LABELS: Record<keyof RegrasSenha, string> = {
  minLength: "Mínimo 8 caracteres (recomendado 10+)",
  uppercase: "Pelo menos 1 letra maiúscula",
  lowercase: "Pelo menos 1 letra minúscula",
  digit: "Pelo menos 1 dígito",
  special: "Pelo menos 1 caractere especial (!@#$%...)",
  noUsername: "Não pode conter o nome do usuário",
};
