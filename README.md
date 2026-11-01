# psylog

Is a flexibly extendable logging class to write the onsets of events in experiments
in psychology or cognitive neuroscience to a file. 

It tries to adhere to [BIDS](bids-specification.readthedocs.io/en/stable/) standards and is in large parts developed
with users of [PsychoPy](https://psychopy.org/) in mind.

| :warning: A note on timing   |
|----------------------------------------------|
| I haven't tested this implementation with regards to ms precision in timing. Be very careful and do your own assessments, when using these tools for e.g. EEG experimentation!|

## Features

* Flexible logging of events
* On the fly calculation of reaction times
* Outputs trying to adhere to the BIDS standard (defaults)
* Has some input validation.
* With a little extra effort can write an `events.json` sidecar.

Enhancement plans:

* fMRI trigger logging
* Using `events.json` for proper data reading to pandas.
* Proper validation and creation of logger from compatible `events.json`. 

In a future release the logger will replace logging in [rewardGym]|(https://github.com/rewardMap/rewardGym), a toolbox
trying to streamline reinforcement learning experiments for humans. 

## Installation

The main package is pure python, so there are no other dependencies. Python >= 3.10 is supported.

## Main philosophy

The main components of this package are the logger and category classes.

For example a simple logger, only having mandatory BIDS fields for `onset`, `duration`, and `trial_type` will
be instantiated as:

```python
import time
from psylog import BaseLogger

# The BaseLogger will default to system time as a default clock.
logger = BaseLogger(file_name="test.tsv")
# Create the first row of the tsv file and open the file:
logger.create()
# The logger will now write each new line to the file.

# The main function is the logging of events - the value of each column can be set here:
logger.log_event({
    "trial_type": "stimulus1"
})
# The logger will infer the onset time using the logger's clock.

# A special functionality is determining the duration of an event, by providing
# the original onset:
onset_stim2 = logger.get_time()

time.sleep(1.0)

logger.log_event({
    "trial_type": "stimulus2",
},
onset=onset_stim2)

# At the end of the experiment the logger should be closed:
logger.close()
```

### The categories

The logger is augmented using the `CategoryConfig` class.

```python
@dataclass
class CategoryConfig:
    """
    CategoryConfig is the config class that handles how the logger handles each category it is logging.
    """
    name: str # Name of category and the column in the logfile
    default: Any # The default value - should be provided during construction
    mode: LogMode = LogMode.EVENT # See LogMode enum for more information.

    # Validation
    data_type: type | tuple[type, ...] | None = None # Which data-type is expected, if None everything goes
    allow_na: bool = True # If non finite values or "n/a" as a sring is allowed.

    # BIDS metadata
    description: str = "" # Descriptions in BIDS sidecare (events.json)
    units: str = "n/a" # Which units are being logged.
    long_name: str = "" # Long name, when an abbreviation is used. E.g., "stim" and "stimulus"

    # Levels
    levels: dict[str, str] = field(default_factory=dict) # Different levels of the experiment (e.g., trial type.)
                                                         # Is a dictionary to allow descriptions.
    validate_levels: bool = False # If pre-specified levels should be validated (no other input allowed)
    collect_levels: bool = False # If levels should be collected during the logging process.
```

Where the way of logging is defined via `LogMode`s:

```python
class LogMode(Enum):
    """Controls how a category is handled in logging"""

    STATIC = "static"  # Always included in output, does not change during the experiment. E.g. participant id and similar.
    EVENT = "event"  # Provided by the user, uses only provided data at log time.
    IMPLIED = "implied"  # These use specific functions, e.g. clocks of the Logger, so handle with care.
    STATE = "state"  # Takes on a state, that is being logged continuously, states will be overwritten, when new data is logged.
```

### Categories in action

```python
# We use the bids defaults - these can be retrieved via the convenience function get_mandatory_bids_events:
import time
from psylog import LogMode, CategoryConfig, BaseLogger
import pandas as pd

categories = [
    # Onsets are IMPLIED, as they are calculated on the fly (if not provided via the dictionary)
    CategoryConfig(
        name="onset",
        default="n/a",
        mode=LogMode.IMPLIED,
        description="event onset",
        units="seconds",
        data_type=(int, float),
    ),
    # Duration is also IMPLIED as it can be calculated on the fly.
    CategoryConfig(
        name="duration",
        default="n/a",
        mode=LogMode.IMPLIED,
        description="event duration",
        units="seconds",
        data_type=(int, float),
    ),
    # Trial type is only coding for events, so it is not "on" the entire time, by default the events are not
    # valiated but collected:
    CategoryConfig(
        name="trial_type",
        default="n/a",
        mode=LogMode.EVENT,
        description="an event in the experiment",
        units="n/a",
        collect_levels=True,
        data_type=(str),
    ),
    # Trials are counted sequentially - but persistent for each event in a given trial
    CategoryConfig(
        name="trial",
        default=-1,
        mode=LogMode.STATE,
        description="Trial",
        units="arbitrary unit",
        data_type=(int),
    ),
    # Same goes for the current condition - here levels are provided and validated:
    CategoryConfig(
        name="condition",
        default="n/a",
        mode=LogMode.STATE,
        description="Condition",
        units="n/a",
        data_type=(str),
        levels={"go": "", "no-go": ""},
        validate_levels=True,
    ),
    # Trial time is another category, that is IMPLIED and calculated by the logger,
    # it has a default handler - more to this later.
    CategoryConfig(
        name="trial_time", default="n/a", mode=LogMode.IMPLIED, description="time since trial started", units="n/a", data_type=(float, int)
    ),
    # Participant ID is a persistent column during data collection. It's sometimes helpful to include it throughout.
    # It is static as it is not changed throughout the experiment.
    CategoryConfig(name="participant_id", default="sub-001", mode=LogMode.STATIC, description="The participant ID", units="n/a", data_type=(str)),
]

# Loggers can also be created using file_name = None, this will then write everything to a dictionary.
# Static columns can also be added using a dictionary during logger creation.
logger = BaseLogger(file_name=None, categories=categories, static_columns={"experiment": "gonogo"})
logger.create()

for trial, condition in enumerate(["go", "no-go", "go", "no-go"]):
    # The trial time can be reset like this:
    logger.set_trial_time()

    logger.log_event({"trial_type": "trial_start", "condition": condition, "trial": trial})

    stim1_onset = logger.get_time()

    time.sleep(0.5)

    logger.log_event({"trial_type": "stimulus"}, onset=stim1_onset)
    logger.log_event({"trial_type": "trial-end"})

logger.close()

# Collecting the data in a pandas dataframe:
print(pd.DataFrame((logger._output.data)))
# Acces to the different categories and their attributes
print(logger.categories_dict["trial_type"].levels)
# Get a dictionary from the logger to create BIDS Sidecars, can be saved to .json
print(logger.get_bids_sidecar())
# This will create an error:
logger.log_events({"condition": "test"})
```

### Handlers and output:

For now only a short explanation here. The logger uses handlers to deal with
`LogMode.IMPLIED` categories. Two are implemented by default, `onset` and `trial_time`,  (`duration` is 
hardcoded).

Handlers are functions, that take the logger and a category as inputs and return a single value.
For example, the `onset` handler simply returns the `logger.clock` time:
```python
def default_onset_handler(logger: BaseLogger, category: CategoryConfig) -> float:
    """Simple handler for onset times"""
    return logger.get_time()
```
Custom handlers can be added using

```python
logger.add_implied_handler("onset", default_onset_handler)
```

Finally, there are currently two output classes: `FileLogOutput` and `DictLogOutput`, which are
created by default, i.e., `FileLogOutput`, when a `file_name` is provided and `DictLogOutput` when `file_name=None`,
which then collects all the data in a dictionary. In principle these can be expanded on as well.

## Using psylog in PsychoPy Builder

Add the package as a user specified package (i.e. pip install -e .) or install via pip.

### Set-up

In the "BeginExp" tab you first have to initiated the logger. This example here 
uses defaults. But it can be easily extended (see some of the other examples).

The default columns, that should be always be in the logger are (BIDS defaults):

* onset
* duration
* trial_type

PsychoPy adds by default:

* response_time
* response_button
* trial
* trial_time

```python

from psylog import PsychoPyLogger

# This instantiates the logger:
PPL = PsychoPyLogger(
    file_name = f"sub-{expInfo['participant']}_task-{expName}_beh.tsv",
    global_clock = core.Clock(),
    static_columns = {
    "participant": expInfo['participant'],
    "experiment": expName},
)

# The logger needs to be created to write the file and add the column header
PPL.create()
```

### Starting a trial

In the routine that starts your trial, I would recommend to call the `start_trial`
method. Which resets the trial clock and if no argument is provided increases
the internal trial counter by one.

```python
# Increases the trial "state" and uses PsychoPy trial handler (the loop here is called `trials`) to
# to infer the trial number. 

PPL.start_trial(trials.thisTrialN)

# I also like to log the beginning of a trial explicitly.
PPL.log_event(
{"trial_type": f"trial-start"}
)

```

### Dynamically keeping track of stimuli

Using some AI help, I figured out (to hopefully accurately track) on and offsets of stimuli in PsychoPy Builder.

First create information about all the stimuli that should be tracked in the "Begin Routine" tab.

```python
# Define all stimulus names you want to track, in this example there are three audio stimuli, which might 
# differ in length during the experiment. The names have to match the stimulus components in Builder.

stimulus_names = ['sound1', 'sound2', 'sound3']

# Initialize timing dictionary
stimTiming = {}

for name in stimulus_names:
    stimTiming[name] = {"onset": None}

# Track which stimuli are currently active (have started but not stopped)
activeStims = set()
```
Then in the Each Frame tab you can basically poll for every frame if the 
stimulus has started or ended.

```python
# Check each stimulus for status changes
for stimName in stimulus_names:
    # Get the stimulus component from the workspace
    stim = locals().get(stimName)

    if stim is not None:
        if stim.status == STARTED and stimName not in activeStims:
            # Stimulus just started
            stimTiming[stimName]['onset'] = PPL.get_time()
            activeStims.add(stimName)
        elif stim.status != STARTED and stimName in activeStims:
            # Stimulus just stopped
            PPL.log_event({"trial_type": stimName, 
                           "stim_file": stimFile[stimName]
                           },
                          onset=stimTiming[stimName]['onset'])

            activeStims.remove(stimName)
```


## History:

This project developed out of my wish / need to have a logger for experiments that works in a way 
that I like. The basics of the logger have been developed already a couple of years ago and modified for each experiment individually. 

For future experiments,  I wanted to avoid re-implementation and aimed at generalizing the syntax for other studies and
create a proper package. 

When I say experiments here, I am literally talking about experiments in **cognitive neuroscience** and **psychology**.
So it deals mostly with cases where participants press buttons on the keyboard in response to something on a screen.

Maybe you will find this useful. :)

## AI Disclosure

AI models hosted by Ki:connect have been used in the development.
The two models that were used were Qwen3.8 27B and Mistral Small 4 119B 2603.

Initial code already existed and was expanded. Some of the original code used
Chat-GPT in the creation process.

Chat-GPT and AI models above were also used to create the tests for this package.