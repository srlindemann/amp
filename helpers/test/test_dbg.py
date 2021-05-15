import logging

import helpers.dbg as dbg
import helpers.unit_test as hut

_LOG = logging.getLogger(__name__)

# TODO(gp): Make sure the coverage is 100%.

# #############################################################################


# TODO(gp): Use a self.assert_equal() instead of a check_string() since this
#  code needs to be stable.
class Test_dassert1(hut.TestCase):
    """
    Test `dassert()`.
    """

    def test1(self) -> None:
        """
        An assertion that is verified.
        """
        dbg.dassert(True)

    def test2(self) -> None:
        """
        An assertion that is not verified.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert(False)
        self.check_string(str(cm.exception))

    def test3(self) -> None:
        """
        An assertion with a message.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert(False, msg="hello")
        self.check_string(str(cm.exception))

    def test4(self) -> None:
        """
        An assertion with a message to format.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert(False, "hello %s", "world")
        self.check_string(str(cm.exception))

    def test5(self) -> None:
        """
        Too many parameters.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert(False, "hello %s", "world", "too_many")
        self.check_string(str(cm.exception))

    def test6(self) -> None:
        """
        Not enough parameters.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert(False, "hello %s")
        self.check_string(str(cm.exception))

    def test7(self) -> None:
        """
        Common error of calling `dassert` instead of `dassert_eq`.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert(y, ["hello"])
        self.check_string(str(cm.exception))


# #############################################################################


class Test_dassert_eq1(hut.TestCase):
    def test1(self) -> None:
        dbg.dassert_eq(1, 1)

    def test2(self) -> None:
        dbg.dassert_eq(1, 1, msg="hello world")

    def test3(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_eq(1, 2, msg="hello world")
        self.check_string(str(cm.exception))

    def test4(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_eq(1, 2, "hello %s", "world")
        self.check_string(str(cm.exception))

    def test5(self) -> None:
        """
        Raise assertion with incorrect message.
        """
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_eq(1, 2, "hello %s")
        self.check_string(str(cm.exception))


# #############################################################################


# TODO(gp): Break it in piece.
class Test_dassert_misc1(hut.TestCase):
    def test1(self) -> None:
        dbg.dassert_in("a", "abc")

    def test2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_in("a", "xyz".split())
        self.check_string(str(cm.exception))

    # dassert_is

    def test3(self) -> None:
        a = None
        dbg.dassert_is(a, None)

    def test4(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_is("a", None)
        self.check_string(str(cm.exception))

    # dassert_isinstance

    def test5(self) -> None:
        dbg.dassert_isinstance("a", str)

    def test6(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_isinstance("a", int)
        self.check_string(str(cm.exception))

    # dassert_set_eq

    def test7(self) -> None:
        a = [1, 2, 3]
        b = [2, 3, 1]
        dbg.dassert_set_eq(a, b)

    def test8(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [2, 2, 1]
            dbg.dassert_set_eq(a, b)
        self.check_string(str(cm.exception))

    # dassert_is_subset

    def test9(self) -> None:
        a = [1, 2]
        b = [2, 1, 3]
        dbg.dassert_is_subset(a, b)

    def test10(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [4, 2, 1]
            dbg.dassert_is_subset(a, b)
        self.check_string(str(cm.exception))

    # dassert_not_intersection

    def test11(self) -> None:
        a = [1, 2, 3]
        b = [4, 5]
        dbg.dassert_not_intersection(a, b)

    def test12(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [4, 2, 1]
            dbg.dassert_not_intersection(a, b)
        self.check_string(str(cm.exception))

    # dassert_no_duplicates

    def test13(self) -> None:
        a = [1, 2, 3]
        dbg.dassert_no_duplicates(a)

    def test14(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 3, 3]
            dbg.dassert_no_duplicates(a)
        self.check_string(str(cm.exception))

    # dassert_eq_all

    def test15(self) -> None:
        a = [1, 2, 3]
        b = [1, 2, 3]
        dbg.dassert_eq_all(a, b)

    def test16(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [1, 2, 4]
            dbg.dassert_eq_all(a, b)
        self.check_string(str(cm.exception))


# #############################################################################


class Test_dassert_lgt1(hut.TestCase):
    def test1(self) -> None:
        dbg.dassert_lgt(0, 0, 3, lower_bound_closed=True, upper_bound_closed=True)

    def test2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_lgt(
                0, 0, 3, lower_bound_closed=False, upper_bound_closed=True
            )
        act = str(cm.exception)
        exp = ""
        self.assert_equal(act, exp)

    def test3(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            lower_bound_closed = False
            upper_bound_closed = True
            dbg.dassert_lgt(
                0,
                100,
                3,
                lower_bound_closed,
                upper_bound_closed,
                "hello %s",
                "world",
            )
        act = str(cm.exception)
        exp = ""
        self.assert_equal(act, exp)


# #############################################################################


class Test_dassert_is_proportion1(hut.TestCase):
    def test1(self) -> None:
        dbg.dassert_is_proportion(0.1, "hello %s", "world")

    def test2(self) -> None:
        dbg.dassert_is_proportion(0.0, "hello %s", "world")

    def test3(self) -> None:
        dbg.dassert_is_proportion(1.0, "hello %s", "world")

    def test_assert1(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_is_proportion(1.01, "hello %s", "world")
        act = str(cm.exception)
        exp = ""
        self.assert_equal(act, exp)

    def test_assert2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_is_proportion(1.01, "hello world")
        act = str(cm.exception)
        exp = ""
        self.assert_equal(act, exp)

    def test_assert3(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_is_proportion(1.01, "hello", "world")
        act = str(cm.exception)
        exp = ""
        self.assert_equal(act, exp)

    def test_assert4(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            dbg.dassert_is_proportion(1.01, "hello %s %s", "world")
        act = str(cm.exception)
        exp = ""
        self.assert_equal(act, exp)


# #############################################################################


class Test_logging1(hut.TestCase):
    def test_logging_levels1(self) -> None:
        dbg.test_logger()
