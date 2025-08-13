
<!--
IMPORTANT NOTES

1. Use GH flavored markdown when writing your description:
   https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax

2. If all boxes in the PR Checklist cannot be checked, this PR should be marked as a draft.

3. DO NOT DELETE ANYTHING FROM THIS TEMPLATE. If a section does not apply to you, simply write
   "N/A" in the description.

4. Code snippets to highlight new, modified, or problematic functionality are highly encouraged,
   though not required. Be sure to use proper code highlighting as demonstrated below.

   ```python
    def a_func():
        return 1

    a = 1
    b = a_func()
    print(a + b)
    ```
-->

<!--The title should clearly define your contribution succinctly.-->
# Add meaningful title here

<!-- Describe your feature here. Please include any code snippets or examples in this section. -->

## Type of Contribution
<!-- Check all that apply to help reviewers understand your contribution -->
- [ ] New Technology Model
- [ ] Bug Fix
- [ ] Feature Enhancement
- [ ] Documentation Update
- [ ] Infrastructure/CI Changes
- [ ] Other (please describe):

## General PR Checklist

<!--Tick these boxes if they are complete, or format them as "[x]" for the markdown to render. -->
- [ ] `CHANGELOG.md` has been updated to describe the changes made in this PR
- [ ] Documentation
  - [ ] Docstrings are up-to-date
  - [ ] Related `docs/` files are up-to-date, or added when necessary
  - [ ] Documentation has been rebuilt successfully
  - [ ] Examples have been updated (if applicable)
- [ ] Tests pass (If not, and this is expected, please elaborate in the tests section)
- [ ] Added tests for new functionality or bug fixes
- [ ] PR description thoroughly describes the new feature, bug fix, etc.

## New Technology Checklist
<!-- Complete this section only if you checked "New Technology Model" above -->
- [ ] **Performance Model**: Technology performance model has been implemented and follows H2Integrate patterns
- [ ] **Cost Model**: Technology cost model has been implemented (if applicable)
- [ ] **Tests**: Unit tests have been added for the new technology
  - [ ] Performance model tests
  - [ ] Cost model tests (if applicable)
  - [ ] Integration tests with H2Integrate system
- [ ] **Example**: A working example demonstrating the new technology has been created
  - [ ] Example has been tested and runs successfully
  - [ ] Example is documented with clear explanations
- [ ] **Documentation**:
  - [ ] Technology documentation page added to `docs/technology_models/`
  - [ ] Technology added to the main technology models list in documentation
- [ ] **Integration**: Technology has been properly integrated into H2Integrate
  - [ ] Added to `supported_models.py`
  - [ ] Follows established naming conventions, e.g. input/output names

## Related issues

<!--If one exists, link to a related GitHub Issue.-->


## Impacted areas of the software

<!--
Replace the below example with any added or modified files, and briefly describe what has been changed or added, and why.
-->
- `path/to/file.extension`
  - `method1`: What and why something was changed in one sentence or less.

## Additional supporting information

<!--Add any other context about the problem here.-->


## Test results, if applicable

<!--
Add the results from unit tests and regression tests here along with justification for any
failing test cases.
-->


<!--
__ For NREL use __
Release checklist:
- [ ] Update the version in h2integrate/__init__.py
- [ ] Verify docs builds correctly
- [ ] Create a tag on the main branch in the NREL/H2Integrate repository and push
- [ ] Ensure the Test PyPI build is successful
- [ ] Create a release on the main branch
-->
