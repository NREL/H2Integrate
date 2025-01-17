# Development guidelines

```{note}
This document is a work in progress and ODIES is rapidly evolving; we'll continue to add to these guidelines as we develop the tool.
```

We've already had divergent codebases in the future due to fast-paced project needs and tight timelines.
To make this better, we're trying to standardize the way we develop code for ODIES in a way that's beneficial for developers, does not slow progress, and is sustainable for the future.
This document outlines the guidelines for developing code for ODIES

## Test development

Each new feature or bug fix should have a corresponding test.
Additionally, to help users create subsystems with the correct methods and attributes, we should have tests that users can run to check their technology models.

First, we will define different types of tests that we have in ODIES:
- Unit tests: tests for individual functions or methods
- Integration tests: tests for the interaction between different functions or methods
- Regression tests: tests for ensuring that new changes do not break existing functionality

### Test location

Each folder within the `ODIES` package should have a corresponding `tests` folder.
For example, the `ODIES/converters/hydrogen` folder should have a `ODIES/converters/hydrogen/tests` folder that contains tests for the functions and classes in the `hydrogen` folder.
This makes it easier to track the corresponding tests for each file.
This organization also allows you to easily run `pytest` on a specific folder as you're modifying files in that folder.

### Regression testing

Optimally, the values used in regression tests should be change unless you've made modifications to the code that would change the expected output and you're aware of the implications of that change.
This is to ensure that the tests are consistent and that changes in the code are intentional.
If a regression test fails when you modify the code and you did not expect it to, you should investigate why the test failed and update the test only if necessary.
This should be explicitly mentioned in the PR process so others are aware of the change.

## Documentation development

The key to making ODIES more user-friendly is to have clear and concise documentation.
This includes docstrings for functions and classes, as well as high-level documentation for the tool itself.
We should also have a clear way to document the expected methods and attributes of classes so that users can develop their own models.

## Misc. development guidelines

- use Google style for docstrings
- use numpy instead of lists for arrays
- use type hints for function arguments and return values
