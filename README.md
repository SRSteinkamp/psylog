# psylog

An attempt at writing generalized loggers, that work well for me.

And maybe for you :)


# AI Disclosure

AI models hosted by Ki:connect have been used in the development.
The two models that were used were Qwen3.8 27B and Mistrall Small 4 119B 2603.

Initial code already existend and was expanded. Some of the original code used
Chat-GPT in the creation process.


# Example for logging and setting up in PsychoPy Builder

Add the package as a user specified package (i.e. pip install -e .).

```python
# In the BeginExp tab place something like this:
# This creates a default logger with an extra "phase" state that logs
# if it is a main or a training trial.

from psylog import PsychoPyLogger
from psylog.schema_helper import get_psychopy_fields, get_mandatory_bids_events
from psylog.log_schema import LogMode, CategoryConfig

categories = get_mandatory_bids_events() + get_psychopy_fields() + [CategoryConfig(name="phase", mode=LogMode.STATE, default="n/a")]

PPL = PsychoPyLogger(
    file_name = f"sub-{expInfo['participant']}_task-{expName}_beh.tsv",
    global_clock = core.Clock(),
    categories = categories,
    static_columns = {
    "participant": expInfo['participant'],
    "experiment": expName},
)

PPL.create()
```

In the beginning of each trial, the trial
can be set:

```python
# Overwrites the trial number (if None, it would increase by one and resets the clock of the current trial.)

PPL.start_trial(trials.thisTrialN)

PPL.log_event(
{"trial_type": f"trial-{tapping_duration}",
"phase": phase}
)
```

Again using some AI help - I managed to hopefully accurately trakc the on and offset of stimuli in the PsychoPy Builder:

In the BeginRoutine Tab:
```python
# Define all stimulus names you want to track
stimulus_names = ['task1_1', 'task1_2', 'task1_3', 'task2_1', 'task2_2','task2_3', 'task3', 'equals', 'then']
stim_files = [t1_1_name, t1_2_name, t1_3_name,
               t2_1_name, t2_2_name, t2_3_name,
               t3_name, "equal", "then"]
stimFile = {}
c = 0
for sn in stimulus_names:
    stimFile[sn] = stim_files[c]
    c+= 1

# Initialize timing dictionary
stimTiming = {}

for name in stimulus_names:
    stimTiming[name] = {"onset": None, "Offset": None}

# Track which stimuli are currently active (have started but not stopped)
activeStims = set()
```

And then basically poll for every frame if an onset and offset have occured:

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
            PPL.log_event({"trial_type": stimName, "stim_file": stimFile[stimName]},
            onset=stimTiming[stimName]['onset'])
            # offset is not really needed
            stimTiming[stimName]['offset'] = core.monotonicClock.getTime()
            activeStims.remove(stimName)
```
