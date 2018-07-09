# Prerequisites

Usma assumes you have `python`, `pip` and `make`.

# Building

```
make build
```

# Running

You will need a local config file `settings/mysettings.py` (or whatever the name),
which should contain variables just as in `settings/example.py`.

Then you run USMA using this configuration:

```
make run-mysettings
```

USMA will use settings from the file given after `run-`.
