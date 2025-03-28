# Class structure in H2Integrate

A major focus of H2Integrate is modularizing the components and system architecture so it's easier to construct and analyze complex hybrid power plants producing commodities for a variety of uses.
As such, we've taken great care to develop a series of base classes and inherited classes to help users develop their own models.

## Base classes

We previously discussed converters, transporters, and storage components.
These components each have an associated base class that contain the methods expected and used for each of those components.
These base classes live within the `core` directory of H2Integrate.

## Inherited classes

Individual technology classes could inherit directly from these base classes, but we do not encourage this within H2Integrate.
Instead, we have an additional layer of class inheritance that helps reduce duplicated code and potential errors.

Let us take a PEM electrolyzer model as an example.
Each electrolyzer model has shared methods and attributes that would be present in any valid model.
These methods are defined at the `ElectrolyzerBaseClass` level, which inherits from `ConverterBaseClass`.
Any implemented electrolyzer model should inherit from `ElectrolyzerBaseClass` to make use of its already built out structure and methods.
This is shown below.

![Class structure](fig_of_class_structure.png)
