import unittest
from itertools import permutations
from hypothesis import given, settings
import hypothesis.strategies as st

from simulation_int_many import geometric_mean
from simulation_int_many import reduction_coefficient
from simulation_int_many import Curve
from simulation_int_many import solve_x
from simulation_int_many import solve_D

MAX_EXAMPLES_MEAN = 20000
MAX_EXAMPLES_RED = 20000
MAX_EXAMPLES_D = 10000
MAX_EXAMPLES_Y = 5000
MAX_EXAMPLES_YD = 100000
MAX_EXAMPLES_NOLOSS = 100000
MIN_FEE = 5e-5

MIN_XD = 10**16
MAX_XD = 10**20


# Test with 3 coins for simplicity
class TestCurve(unittest.TestCase):
    @given(
           st.integers(10**9, 10**15 * 10**18),
           st.integers(10**9, 10**15 * 10**18),
           st.integers(10**9, 10**15 * 10**18)
    )
    @settings(max_examples=MAX_EXAMPLES_MEAN)
    def test_geometric_mean(self, x, y, z):
        val = geometric_mean([x, y, z])
        assert val > 0
        diff = abs((x * y * z)**(1/3) - val)
        assert diff / val <= max(1e-10, 1/min([x, y, z]))

    @given(
           st.integers(10**9, 10**15 * 10**18),
           st.integers(10**9, 10**15 * 10**18),
           st.integers(10**9, 10**15 * 10**18),
           st.integers(10**10, 10**18)
    )
    @settings(max_examples=MAX_EXAMPLES_RED)
    def test_reduction_coefficient(self, x, y, z, gamma):
        coeff = reduction_coefficient([x, y, z], gamma)
        assert coeff <= 10**18

        K = 3**3 * x*y*z / (x + y + z)**3
        if gamma > 0:
            K = (gamma/1e18) / ((gamma/1e18) + 1 - K)
        assert abs(coeff/1e18 - K) <= 1e-7

    @given(
           A=st.integers(1, 10000),
           x=st.integers(10**9, 10**15 * 10**18),  # 1e-9 USD to 1e15 USD
           yx=st.integers(10**11, 10**18),  # <- ratio 1e18 * y/x, typically 1e18 * 1
           zx=st.integers(10**11, 10**18),  # <- ratio 1e18 * z/x, typically 1e18 * 1
           perm=st.integers(0, 5),  # <- permutation mapping to values
           gamma=st.integers(10**10, 10**16)  # gamma from 1e-8 up to 0.01
    )
    @settings(max_examples=MAX_EXAMPLES_D)
    def test_D_convergence(self, A, x, yx, zx, perm, gamma):
        # Price not needed for convergence testing
        pmap = list(permutations(range(3)))

        y = x * yx // 10**18
        z = x * zx // 10**18
        curve = Curve(A, gamma, 10**18, 3)
        curve.x = [0] * 3
        i, j, k = pmap[perm]
        curve.x[i] = x
        curve.x[j] = y
        curve.x[k] = z
        assert curve.D() > 0

    @given(
           st.integers(1, 10000),
           st.integers(10**17, 10**15 * 10**18),  # $0.1 .. $1e15
           st.integers(10**15, 10**21),
           st.integers(10**15, 10**21),
           st.integers(10**10, 10**16),  # gamma from 1e-8 up to 0.01
           st.integers(0, 2),
           st.integers(0, 2),
           st.integers(10**15, 10**21)
    )
    @settings(max_examples=MAX_EXAMPLES_Y)
    def test_y_convergence(self, A, x, yx, zx, gamma, i, j, inx):
        if i == j:
            return
        in_amount = x * inx // 10**18
        y = x * yx // 10**18
        z = x * zx // 10**18
        curve = Curve(A, gamma, 10**18, 3)
        curve.x = [x, y, z]
        out_amount = curve.y(in_amount, i, j)
        assert out_amount > 0

    @given(
           st.integers(1, 10000),
           st.integers(10**17, 10**15 * 10**18),  # 0.1 USD to 1e15 USD
           st.integers(5 * 10**14, 20 * 10**20),
           st.integers(5 * 10**14, 20 * 10**20),
           st.integers(10**10, 10**16),  # gamma from 1e-8 up to 0.01
           st.integers(0, 2),
           st.integers(0, 2),
           st.integers(3 * 10**15, 3 * 10**20)
    )
    @settings(max_examples=MAX_EXAMPLES_NOLOSS)
    def test_y_noloss(self, A, x, yx, zx, gamma, i, j, inx):
        if i == j:
            return
        y = x * yx // 10**18
        z = x * zx // 10**18
        curve = Curve(A, gamma, 10**18, 3)
        curve.x = [x, y, z]
        in_amount = x * inx // 10**18
        try:
            out_amount = curve.y(in_amount, i, j)
            D1 = curve.D()
        except ValueError:
            return  # Convergence checked separately - we deliberately try unsafe numbers
        is_safe = all(f >= MIN_XD and f <= MAX_XD for f in [xx * 10**18 // D1 for xx in curve.x])
        curve.x[i] = in_amount
        curve.x[j] = out_amount
        try:
            D2 = curve.D()
        except ValueError:
            return  # Convergence checked separately - we deliberately try unsafe numbers
        is_safe &= all(f >= MIN_XD and f <= MAX_XD for f in [xx * 10**18 // D2 for xx in curve.x])
        if is_safe:
            assert 2 * (D1 - D2) / (D1 + D2) < MIN_FEE  # Only loss is prevented - gain is ok

    @given(
           st.integers(1, 10000),
           st.integers(10**17, 10**15 * 10**18),  # 0.1 USD to 1e15 USD
           st.integers(MIN_XD, MAX_XD),
           st.integers(MIN_XD, MAX_XD),
           st.integers(MIN_XD, MAX_XD),
           st.integers(10**10, 10**16),  # gamma from 1e-8 up to 0.01
           st.integers(0, 2),
    )
    @settings(max_examples=MAX_EXAMPLES_YD)
    def test_y_from_D(self, A, D, xD, yD, zD, gamma, j):
        xp = [D * xD // 10**18, D * yD // 10**18, D * zD // 10**18]
        y = solve_x(A, gamma, xp, D, j)
        xp[j] = y
        D2 = solve_D(A, gamma, xp)
        assert 2 * (D - D2) / (D2 + D) < MIN_FEE  # Only loss is prevented - gain is ok


if __name__ == "__main__":
    unittest.main()
