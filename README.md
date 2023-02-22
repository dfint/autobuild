# autobuild

An automated repository which builds csv files with a translation for several languages to use with [dfint/df-steam-hook](https://github.com/dfint/df-steam-hook). Updates once a day on data from [dfint/translations-backup](https://github.com/dfint/translations-backup).

It uses encodings specified in [config.yaml](config.yaml). For some of the languages the encoding is set to utf-8 (even though utf-8 is not supported by df-steam-hook), just to do at least some automation for these languages.

In the future here will be implemented an autobuild of a mod group to translate external files (`Dwarf Fortress/data/vanilla`) and autogeneration of a graphic font using [dfint/df-font-generator](https://github.com/dfint/df-font-generator).
