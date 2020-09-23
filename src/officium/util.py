_units_map     = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']
_tens_map      = ['', 'X', 'XX', 'XXX', 'XL', 'L', 'LX', 'LXX', 'LXXX', 'XC']
_hundreds_map  = ['', 'C', 'CC', 'CCC', 'CD', 'D', 'DC', 'DCC', 'DCCC', 'CM']
def roman(n):
    """Returns the Roman numeral encoding of the integer n."""
    assert n > 0
    assert n < 4000

    thousands, n = divmod(n, 1000)
    hundreds, n = divmod(n, 100)
    tens, units = divmod(n, 10)

    return ''.join('M' * thousands, _hundreds_map[hundreds], _tens_map[tens],
                   _units_map[units])
