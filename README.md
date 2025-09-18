# autobuild

> [!IMPORTANT]  
> You don't need to put things together manually anymore. Just use the [installer](https://github.com/dfint/installer) or the [package builder](https://dfint-package-build.streamlit.app).

This is an automated repository which builds csv files with a translation for several languages to use with [dfint/df-steam-hook-rs](https://github.com/dfint/df-steam-hook-rs) (and earlier with [dfint/df-steam-hook](https://github.com/dfint/df-steam-hook)). It updates twice a day on data from [dfint/translations-backup](https://github.com/dfint/translations-backup).

Ready to use csv files are in the [translation_build](https://github.com/dfint/autobuild/tree/main/translation_build) directory.
It contains two more directories: `csv` and `csv_with_objects`. The first one contains csv files with text only from `hardcoded` resource on transifex (only text from the exe file of the game). The second one additionaly contains text from the `objects` resource (animals, ores, stones, plants and other things).

Also, next to csv files in the `csv_with_objects` directory there are files with list of errors which were found during processing the objects.po resource file.

To download a file you need to open it (click on it in the file list), then click on "Download raw file" icon button in the top right area of the file area.

Files are encoded in encodings specified in [config.yaml](config.yaml). For some of the languages the encoding is set to utf-8 (even though utf-8 is not supported by df-steam-hook), just to do at least some automation for these languages.

### Adding languages to autobuild

If your language is missing, although it is present on [transifex](https://app.transifex.com/dwarf-fortress-translation/dwarf-fortress-steam/dashboard/) and [dfint/translations-backup](https://github.com/dfint/translations-backup), please create an [issue](https://github.com/dfint/autobuild/issues) and specify your language and desired encoding (we'll try best to figure out the encoding, if you are not sure which encoding do you need).

If the language is missing on transifex too, create a request to add the language there.

Keep in mind, that some languages cannot be used with Dwarf Fortress at the moment (at least with our version of **df-steam-hook-rs**): in particular, no languages with rigt-to-left and hieroglyphic wrighting systems are supported.
