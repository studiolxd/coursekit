"""The html assembly backend: the plan of a unit (the same one the creator backend loads) rendered as a SCORM package of its own.

`render` turns each brick into HTML (one function per component), `build` bundles the player (SCORM runtime and the behaviour of
the components), writes the manifest and zips the unit, `check` verifies that the package carries every word of the content.
"""
