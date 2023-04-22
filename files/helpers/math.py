
def remap(input: float, smin: float, smax: float, emin: float, emax: float) -> float:
    t = (input - smin) / (smax - smin)
    return (1 - t) * emin + t * emax

def clamp(input: float, min: float, max: float) -> float:
    if input < min: return min
    if input > max: return max
    return input

def saturate(input: float) -> float:
    return clamp(input, 0, 1)

def lerp(a: float, b: float, t: float) -> float:
    return (1 - t) * a + t * b
