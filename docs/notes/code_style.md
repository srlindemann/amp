# Style guide references

- We care about at consistency rather than arguing about which approach is better
    - E.g., see "tab vs space" flame-war from the 90s
- Unless explicitly noted we prefer to follow the style guide below

- As a rule of thumb we default to Google style unless Python community (in the
  form of PEP) or tools we rely favor another style

## Reference

- Google Python Style Guide (GPSG)
  - `https://google.github.io/styleguide/pyguide.html`

- Commenting style
    - `http://www.sphinx-doc.org/en/master/`
    - `https://thomas-cokelaer.info/tutorials/sphinx/docstring_python.html`

- Code convention PEP8
    - `https://www.python.org/dev/peps/pep-0008/`

- Documentation best practices
    - `https://github.com/google/styleguide/blob/gh-pages/docguide/best_practices.md`

- Philosophical stuff
    - `https://github.com/google/styleguide/blob/gh-pages/docguide/philosophy.md`

- Unix rules (although a bit cryptic sometimes)
    - `https://en.wikipedia.org/wiki/Unix_philosophy#Eric_Raymond%E2%80%99s_17_Unix_Rules`

# Comments

## Docstring conventions

- Code needs to be properly commented

- We follow python standard [PEP257](https://www.python.org/dev/peps/pep-0257/)
  for commenting
    - PEP257 standardizes what and how comments should be expressed (e.g., use a
      triple quotes for commenting a function), but it does not specify what
      markup syntax should be used to describe comments

- Different conventions have been developed for documenting interfaces
    - reST
    - Google (which is cross-language, e.g., C++, python, …)
    - epytext
    - numpydoc

## reST style

- reST (aka re-Structured Text) style is:
    - the most widely supported in the python commpunity
    - supported by all doc generation tools (e.g., epydoc, sphinx)
    - default in pycharm
    - default in pyment
    - supported by pydocstyle (which does not support Google style as explained
      [here](https://github.com/PyCQA/pydocstyle/issues/275))

```python
"""
This is a reST style.

:param param1: this is a first param
:type param1: str
:param param2: this is a second param
:type param2: int
:returns: this is a description of what is returned
:rtype: bool
:raises keyError: raises an exception
"""
```

## Descriptive vs imperative style

- GPSG suggests to use descriptive style of comments, e.g., "This function does
  this and that", instead than imperative style "Do this and that"

- [PEP-257](https://www.python.org/dev/peps/pep-0257/)
    ```
    The docstring is a phrase ending in a period. It prescribes the function or
    method's effect as a command ("Do this", "Return that"), not as a description;
    e.g. don't write "Returns the pathname ...".
    ```
    - pylint and other python QA tools favor an imperative style
    - Since we prefer to rely on automatic checks, we decided to use an imperative
      style of comments

### Alternate parameter description and type

- We prefer to alternate param description and its type so the docstring below,
  although good, does not follow our convention
    *Bad**
    ```python
    :param data: CB data
    :param metrics: CB metrics
    :param fill_na_w_zero: If True, fill NaN values with zeros.

    :type data: pd.DataFrame
    :type metrics: list of str
    :type fill_na_w_zero: bool

    :returns data_merged: Data with two metrics added together.
    :rtype data_merged: pd.DataFrame
    ```

- The code should be changed into:
    **Good**
    ```python
    :param data: CB data
    :type data: pd.DataFrame
    :param metrics: CB metrics
    :type metrics: list of str
    :param fill_na_w_zero: If True, fill NaN values with zeros.
    :type fill_na_w_zero: bool

    :returns data_merged: Data with two metrics added together.
    :rtype data_merged: pd.DataFrame
    ```

- We pick lowercase after `:param XYZ: ...` unless the first word is a proper
  noun or type

- Examples are [here](https://stackoverflow.com/questions/3898572)

### Avoid empty lines in code

- If you feel that you need an empty line in the code, it probably means that a
  specific chunk of code is a logical piece of code performing a cohesive
  function.
    ```python
    ...
    end_y = end_dt.year
    # Generate list of file paths for ParquetDataset.
    paths = list()
    ...
    ```

- Instead of putting an empty line, you should put a comment describing at high
  level what the code does.
    ```python
    ...
    end_y = end_dt.year
    # Generate list of file paths for ParquetDataset.
    paths = list()
    ...
    ```

- If you don't want to add just use an empty comment.
    ```python
    ...
    end_y = end_dt.year
    #
    paths = list()
    ...
    ```

- The problem with empty lines is that they are visually confusing since one
  empty line is used also to separate functions. For this reason we suggest to
  use an empty comment.

### Avoid distracting comments

- Use comments to explain the high level logic / goal of a piece of code and not
  the details
    - E.g., do not comment things that are obvious, e.g.,
    ```python
    # Print results.
    log.info("Results are %s", ...)
    ```

### If you find a bug, obsolete docstring in the code
- The process is:
    - do a `git blame` to find who wrote the code
    - if it's an easy bug, you can fix it and ask for a review to the author
    - you can file a comment on Upsource
    - you can file a bug on Github with
        - clear info on the problem
        - how to reproduce it, ideally a unit test
        - stacktrace
        - you can use the tag “BUG: ..."

# Logging

## Always use logging instead of prints
- Always use logging and never `print()` to report debug, info, warning 

## Our logging idiom
```python
import helpers.dbg as dbg

_LOG = logging.getLogger(__name__)

dbg.init_logger(verb=logging.DEBUG)

_LOG.debug("I am a debug function about %s", a)
```

- In this way one can decide how much debug info are needed (see Unix rule of
  silence)
    - E.g., when there is a bug one can run with `-v DEBUG` and see what's
      happening right before the bug

## Logging level

- Use `_LOG.warning` for messages to the final user related to something
  unexpected where the code is making a decision that might be controversial
    - E.g., processing a dir that is supposed to contain only `.csv` files
      the code finds a non-`.csv` file and decides to skip it, instead of
      breaking

- Use `_LOG.info` to communicate to the final user, e.g.,
    - when the script is started
    - where the script is saving its results
    - a progress bar indicating the amount of work completed

- Use `_LOG.debug` to communicate information related to the internal behavior of
  code
    - Do not pollute the output with information a regular user does not care
      about

- Make sure the script prints when the work is terminated, e.g., "DONE" or
  "Results written in ..."
    - This is useful to indicate that the script did not die in the middle:
      sometimes this happens silently and it is reported only from the OS return
      code

## Use positional args when logging

- Instead of doing this:
    **Bad**
    ```python
    _LOG.debug('cmd=%s %s %s' % (cmd1, cmd2, cmd3))
    _LOG.debug('cmd=%s %s %s'.format(cmd1, cmd2, cmd3))
    _LOG.debug('cmd={cmd1} {cmd2} {cmd3}')
  do this
    **Good**
    ```
     _LOG.debug('cmd=%s %s %s', cmd1, cmd2, cmd3)
    ```

- The two statements are equivalent from the functional point of view
- The reason is that in the second case the string is not built unless the
  logging is actually performed, which limits time overhead from logging

## Report warnings

- If there is a something that is suspicious but you don't feel like it's
  worthwhile to assert, report a warning with:
```
_LOG.warning(...)
```

- If you know that if there is a warning then there are going to be many many warnings
    - print the first warning
    - send the rest to warnings.log
    - at the end of the run, reports "there are warnings in warnings.log"

# Assertion

## Use positional args when asserting
- `dassert_*` is modeled after logging so for the same reasons one should use
  positional args
    **Bad**
    ```python
    dbg.dassert_eq(a, 1, "No info for %s" % method)
    ```
    **Good**
    ```python
    dbg.dassert_eq(a, 1, "No info for %s", method)
    ```

# Import

## Importing code from Git submodule
- If you are in `p1` and you need to import something from `amp`:
    - **Bad**
        ```python
        import amp.helpers.dbg as dbg
        ```
    - **Good**
        ```python
        import helpers.dbg as dbg
        ```

- We map submodules using `PYTHONPATH` so that the imports are independent from
  the position of the submodule

- In this way code can be moved across repos without changing the imports

## Don't use evil "import *"

- Do not use in notebooks or code this evil import
    - **Bad**
        ```python
        from edgar.utils import *
        ```
    - **Good**
        ```python
        import edgar.utils as edu
        ```
- The` from ... import *`
    - pollutes the namespace with the symbols and spreads over everywhere, making
      painful to clean up
    - makes unclear from where each function is coming from, losing context that
      comes from the namespace
    - is evil in many other ways (see
      [StackOverflow](https://stackoverflow.com/questions/2386714/why-is-import-bad))

## Cleaning up the evil `import *`
- To clean up the mess you can:
    - for notebooks
        - find & replace (e.g., using jupytext and pycharm)
        - change the import and run one cell at the time
    - for code
        - change the import and use linter on file to find all the problematic
          spots

- One of the few spots where the evil import * is ok is in the `__init__.py` to
  tweak the path of symbols exported by a library
    - This is an advanced topic and you should rarely use it

## Avoid `from ... import ...`

- Importing many different functions, like:
    - **Bad**
    ```python
    from edgar.officer_titles import read_documents, read_test_set, \
        get_titles, split_titles, get_titles_overview, \
        word_pattern, symbol_pattern, exact_title, \
        apply_patterns_to_texts, extract_canonical_names, \
        get_rules_coverage, text_contains_only_canonical_titles, \
        compute_stats, NON_MEANING_PATTERNS_BEFORE, patterns
    ```
    - creates lots of maintenance effort
        - e.g., anytime you want a new function you need to update the import
          statement
    - creates potential collisions of the same name
        - e.g., lots of modules have a `read_data()` function
    - importing directly in the namespace loses information about the module
        - e.g.,` read_documents()` is not clear: what documents?
        - `np.read_documents()` at least give information of which packages
          is it coming from
          
## Examples of imports

- Example 1
    - **Bad**
       ```python
       from edgar.shared import edgar_api as api
    - **Good**
       ```python
       import edgar.shared.edgar_api as edg_api
       ```

- Example 2
   - **Bad**
        ```python
        from edgar.shared import headers_extractor as he
        ```
    - **Good**
        ```python
        import edgar.shared.headers_extractor as he
        ```
      
- Example 3
    - **Bad**
        ```python
        from helpers import dbg
        ```
    - **Good**
        ```python
        import helpers.dbg as dbg
        ```
      
- Example 4
    - **Bad**
        ```python
       from helpers.misc import check_or_create_dir, get_timestamp
        ```
    - **Good**
        ```python
        import helpers.misc as hm
        ```

## Always import with a full path from the root of the repo / submodule

- **Bad**
    ```python
    import timestamp
    ``
- **Good**
    ```
    import compustat.timestamp
    ```
- In this way your code can run without dependency from your current dir

# Python scripts

## Skeleton for a script

- The official reference for a script is `//amp/dev_scripts/script_skeleton.py`
- You can copy this file and change it

## Use the script framework
- We have several libraries that make writing scripts in python very easy, e.g.,
  `//amp/helpers/system_interaction.py`

- As an interesting example of complex scripts you can check out:
  `//amp/dev_scripts/linter.py`

## Python executable characteristics
- All python scripts that are meant to be executed directly should:
    1) be marked as executable files with:
        ```bash
        > chmod +x foo_bar.py
        ```
    2) have the python code should start with the standard Unix shebang notation:
        ```python
        #!/usr/bin/env python
        ```
    - This line tells the shell to use the `python` defined in the conda
      environment

    3) have a:
        ```python
        if __name__ == "__main__":
            ...
        ```
    4) ideally use `argparse` to have a minimum of customization

- In this way you can execute directly without prepending with python

## Use clear names for the scripts

- In general scripts (like functions) should have name like “action_verb”.
    - **Bad**
        - Example of bad names are` timestamp_extractor.py` and
          `timestamp_extractor_v2.py`
            - Which timestamp data set are we talking about?
            - What type of timestamps are we extracting?
            - What is the difference about these two scripts?

- We need to give names to scripts that help people understand what they do and
  the context in which they operate
- We can add a reference to the task that originated the work (to give more
  context)

- E.g., for a script generating a dataset there should be an (umbrella) bug for
  this dataset, that we refer in the bug name, e.g.,`TaskXYZ_edgar_timestamp_dataset_extractor.py`

- Also where the script is located should give some clue of what is related to