import datetime
import logging
from typing import Any

import pandas as pd

import helpers.playback as plbck
import helpers.unit_test as hut

_LOG = logging.getLogger(__name__)


class TestJsonRoundtrip1(hut.TestCase):
    """
    Test roundtrip conversion through jsonpickle for different types.
    """

    def test1(self) -> None:
        obj = 3
        #
        plbck.round_trip_convert(obj, logging.DEBUG)

    def test2(self) -> None:
        obj = "hello"
        #
        plbck.round_trip_convert(obj, logging.DEBUG)

    def test3(self) -> None:
        data = {
            "Product": ["Desktop Computer", "Tablet", "iPhone", "Laptop"],
            "Price": [700, 250, 800, 1200],
        }
        df = pd.DataFrame(data, columns=["Product", "Price"])
        df.index.name = "hello"
        #
        obj = df
        plbck.round_trip_convert(obj, logging.DEBUG)

    def test4(self) -> None:
        obj = datetime.date(2015, 1, 1)
        #
        plbck.round_trip_convert(obj, logging.DEBUG)


class TestPlaybackInputOutput1(hut.TestCase):
    """
    Freeze the output of Playback.
    """

    def _helper(self, mode: str, *args: Any, **kwargs: Any) -> None:
        # Define a function to generate a unit test for.
        def F(a: Any, b: Any) -> Any:
            if isinstance(a, datetime.date) and isinstance(b, datetime.date):
                return abs(a - b)
            if isinstance(a, dict) and isinstance(b, dict):
                c = {}
                c.update(a)
                c.update(b)
                return c
            return a + b

        # Generate a unit test for `F` with Playback.
        playback = plbck.Playback(mode, "F", *args, **kwargs)
        res = F(*args)
        code = playback.run(res)
        # Freeze the Playback output (unit test code).
        self.check_string(code)
        # Execute the unit test code generated by Playback.
        _LOG.debug("Testing code:\n%s", code)
        exec(code, locals())

    def test1(self) -> None:
        """
        Test for int inputs.
        """
        # Create inputs.
        a = 3
        b = 2
        # Generate, freeze and execute a unit test.
        self._helper("assert_equal", a, b)

    def test2(self) -> None:
        """
        Test for string inputs.
        """
        # Create inputs.
        a = "test"
        b = "case"
        # Generate, freeze and execute a unit test.
        self._helper("assert_equal", a, b)

    def test3(self) -> None:
        """
        Test for list inputs.
        """
        # Create inputs.
        a = [1, 2, 3]
        b = [4, 5, 6]
        # Generate, freeze and execute a unit test.
        self._helper("assert_equal", a, b)

    def test4(self) -> None:
        """
        Test for dict inputs.
        """
        # Create inputs.
        a = {"1": 2}
        b = {"3": 4}
        # Generate, freeze and execute a unit test.
        self._helper("assert_equal", a, b)

    def test5(self) -> None:
        """
        Test for pd.DataFrame inputs.
        """
        # Create inputs.
        a = pd.DataFrame({"Price": [700, 250, 800, 1200]})
        b = pd.DataFrame({"Price": [1, 1, 1, 1]})
        # Generate, freeze and execute a unit test.
        self._helper("assert_equal", a, b)

    def test6(self) -> None:
        """
        Test for datetime.date inputs (using `jsonpickle`).
        """
        # Create inputs.
        a = datetime.date(2015, 1, 1)
        b = datetime.date(2012, 1, 1)
        # Generate, freeze and execute a unit test.
        self._helper("assert_equal", a, b)


class TestPlaybackUseCase1(hut.TestCase):
    def test1(self) -> None:
        def F(a: Any, b: Any) -> Any:
            c = a + b
            if use_playback:
                playback = plbck.Playback("assert_equal", "F", a, b)
                # The output is the code of a unit test that checks that `c` is
                # equal to the result of running `F(a, b)` without Playback.
                output = playback.run(c)
                # Return the code.
                res = output
            else:
                # Return the result of running `F(a, b)` without Playback.
                res = c
            return res

        # Execute without Playback.
        a = 3
        b = 2
        use_playback = False
        ret = F(a, b)
        self.assertEqual(ret, 5)
        # Execute with Playback (generating a unit test for `F`).
        a = 3
        b = 2
        use_playback = True
        code = F(a, b)
        self.check_string(code)
        # Execute the unit test generated by Playback (make sure it passes).
        _LOG.debug("Testing code:\n%s", code)
        # We need to disable the unit test generation inside the function `F`.
        use_playback = False
        exec(code, locals())
