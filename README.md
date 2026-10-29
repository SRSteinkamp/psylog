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

In a future release the logger will replaced logging in [rewardGym]|(https://github.com/rewardMap/rewardGym), a toolbox
for experiments with humans in reinforcement learning. 

## History:

This project developed out of my wish / need to have a logger for experiments that works in a way 
that I like. The basics of the logger have been developed already a couple of years ago and modified for each experiment individually. 

For future experiments,  I wanted to avoid re-implementation and aimed at generalizing the syntax for other studies and
create a proper package. 

When I say experiments here, I am literally talking about experiments in **cognitive neuroscience** and **psychology**.
So it deals mostly with cases where participants press buttons on the keyboard in response to something on a screen.

Maybe you will find this useful. :)


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

First create information about all the stimuli that should be tracked in the "BeginnRoutine" tab.

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


## AI Disclosure

AI models hosted by Ki:connect have been used in the development.
The two models that were used were Qwen3.8 27B and Mistrall Small 4 119B 2603.

Initial code already existend and was expanded. Some of the original code used
Chat-GPT in the creation process.