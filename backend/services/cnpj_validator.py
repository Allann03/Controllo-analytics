"""Validação e formatação de CNPJ com verificação dos dígitos verificadores."""


def validar_cnpj(cnpj: str) -> bool:
    """Retorna True se o CNPJ for válido (dígitos verificadores corretos)."""
    nums = "".join(c for c in cnpj if c.isdigit())
    if len(nums) != 14 or nums == nums[0] * 14:
        return False

    def _digito(base: str, pesos: list) -> int:
        soma = sum(int(n) * p for n, p in zip(base, pesos))
        r = soma % 11
        return 0 if r < 2 else 11 - r

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return (
        int(nums[12]) == _digito(nums[:12], pesos1)
        and int(nums[13]) == _digito(nums[:13], pesos2)
    )


def formatar_cnpj(cnpj: str) -> str:
    """Retorna CNPJ no formato XX.XXX.XXX/XXXX-XX (já formatado preservado)."""
    nums = "".join(c for c in cnpj if c.isdigit())
    if len(nums) != 14:
        return cnpj
    return f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:14]}"
