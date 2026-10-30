"""Logger classes used by the experiment."""

import pandas as pd
from rewardgym import get_env
from rewardgym.agents.base_agent import QAgent
from rewardgym.psychopy_render import psychopy_stubs as core
from rewardgym.psychopy_render.logger import SimulationLogger as SMLR
from rewardgym.psychopy_render.psychopy_stubs import Clock, Window, getKeys
from rewardgym.runner import pspy_run_task

from psylog import BaseLogger, DictLogOutput, LogMode

from .rewardgym_legacy_categories import get_rewardmap_defaults

rwm_defaults = get_rewardmap_defaults()


class ExperimentLoggerNew(BaseLogger):
    """
    Logger class to log what is going on during the experiment.
    Now inherits from ParentLogger for BIDS-compliant logging.
    """

    def __init__(
        self,
        file_name: str,
        global_clock: Clock = None,
        participant_id: str = "n/a",
        task: str = "hcp",
        run: int = 1,
        seq_tr: float = 0.752,
        sep: str = "\t",
        na: str = "n/a",
        kill_switch: str = "q",
        mr_trigger: str = "5",
        mr_clock: Clock = None,
        categories: list | None = None
    ):
        """
        Logger class to help with logging during a potential fMRI experiment,
        which is implemented in PsychoPy.

        Parameters
        ----------
        file_name : str
            Name of the output file.
        global_clock : core.Clock
            Clock that is used by the experiment.
        participant_id : str
            The participant id (logged as its own persistent column)
        task : str, optional
            The task, also logged as persistent column, by default "hcp"
        run : int, optional
            The run, also logged as persistent column, by default 1
        seq_tr : float, optional
            If it is an fMRI experiment, this is echo time. Used to calculate the expected collection between acquisitions, by default 0.752
        sep : str, optional
            What kind of separator to use in output file, by default "\t"
        na : str, optional
            How NaN values are written to file, by default "n/a"
        kill_switch : str, optional
            Button to press to exit the experiment, by default "q"
        mr_trigger : str, optional
            Trigger of the MRI (assuming that it is transformed to a key press), by default "5"
        mr_clock : Clock, optional
            Clock for MRI timing, by default same as global_clock
        categories : List, optional
            List of category configurations, by default rewardmap_defaults
        """
        # Set up static columns for participant_id, task, run
        static_columns = {
            "participant_id": participant_id,
            "task": task,
            "run": run
        }

        # Set up clocks
        if global_clock is None:
            global_clock = Clock()

        # Initialize ParentLogger with base parameters
        super().__init__(
            file_name=file_name,
            sep=sep,
            na=na,
            categories=get_rewardmap_defaults(),
            static_columns=static_columns,
            clock = global_clock
        )

        self.global_clock = self.clock
        if mr_clock is None:
            mr_clock = global_clock

        self.mr_clock = mr_clock

        # Experiment-specific parameters
        self.seq_tr = seq_tr
        self.kill_switch = kill_switch
        self.mr_trigger = mr_trigger

        # Initialize trial tracking
        self.trial_start = None
        self.tr = 0
        # Create the file (writes header)
        self.create()

    def log_event(self, info_dict: dict, reward: float | None = None, onset: float | None = None):
        """
        Logs the current event.

        Parameters
        ----------
        info_dict : Dict
            the dictionary that contains the current information of the trial.
        reward : float, optional
            reward received in the trial, by default None
        onset : float, optional
            The real onset of the event, duration is
                calculated between onset and current time, by default None

        Raises
        ------
        ValueError
            Returns an error if onset is after the current time.
        """
        # Add reward to info_dict if provided
        if reward is not None:
            info_dict = info_dict.copy()  # Don't modify original
            info_dict["reward"] = reward

        # Call parent's log_event with our custom onset handling
        super().log_event(info_dict, onset=onset)


    def key_strokes(
        self, win: Window, keyList: list[str] | None = None
    ) -> tuple[str, float] | None:
        """
        Check for key strokes in the keyboard buffer. Checking for MR-triggers,
        close commands (kill_switch), or other allowed responses.

        Parameters
        ----------
        win : Window
            Psychopy window object, used to display the task.
        keyList : List[str], optional
            List of allowed keys., by default []

        Returns
        -------
        Union[Tuple[str, float], None]
            _description_
        """
        if keyList is None:
            keyList = []
        presses = getKeys(timeStamped=self.clock)
        response = None

        if presses:
            for resp in presses:
                if resp[0] == self.kill_switch:
                    # Closes the window, closes the file and quits psychopy.
                    win.close()
                    self.close()
                    core.quit()

                elif resp[0] == self.mr_trigger:
                    self.tr += 1
                    expected_time = self.mr_clock.getTime() - (self.tr * self.seq_tr)
                    # Use parent's log_event
                    self.log_event(
                        {
                            "event_type": "TR",
                            "response_button": resp[0],
                            "response_time": self.mr_clock.getTime(),
                            "expected_duration": expected_time,
                        },
                    )

                elif resp[0] in keyList:
                    # Potentially dangerous - if press is in list, return!
                    response = (resp[0], resp[1])

                else:
                    # Use parent's log_event
                    self.log_event(
                        {
                            "event_type": "button-press",
                            "response_button": resp[0],
                            "response_time": resp[1] - self.trial_start,
                        },
                    )

            return response

        else:
            return response


    def wait(self, win, time: float, start: float | None = None, wait_no_keys: bool = False):
        """
        Wait for a given time.

        Parameters
        ----------
        time : float
            Time to wait, in seconds.
        start : float, optional
            Specify a different time, than the current one of the Logger, by default None
        """
        if time is None:
            return

        if start is None:
            start = self.get_time()

        t_wait = start + time

        # Trying to avoid unnecessary checks
        while t_wait > self.get_time():
            if not wait_no_keys:
                self.key_strokes(win)


    def update_trial_info(self, **kwargs):
        """Update trial-related state information."""
        for k, v in kwargs.items():
            if k in self.categories_dict and self.categories_dict[k].mode == LogMode.STATE:
                self.categories_dict[k].set_state(v)

class SimulationLoggerNew(ExperimentLoggerNew):
    """Simulation version that stores data in memory instead of writing to file."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override the output to use DictLogOutput
        self._output = DictLogOutput()  # From codebase.txt

    def key_strokes(self, key, rt) -> tuple[str, float] | None:
        """Override to work with simulation."""
        return (key, rt)

    def close(self):
        """Return the stored data instead of closing a file."""
        return self._output.data  # Assuming DictLogOutput stores data in self.data

    def wait(self, win, time: float, start: float | None = None):
        """Override wait to work with simulation."""
        if time is None:
            return

        if start is None:
            start = self.get_time()

        self.clock.time += time


def test_regression():

    df_out = []

    for lg in ["newer", "old"]:
        print(lg)
        task = "risk-sensitive"
        env = get_env(task, seed = 10, render_backend = "psychopy-simulate")

        agent = QAgent(
            learning_rate = 0.1,
            temperature = 4,
            discount_factor = 0.99,
            action_space = env.n_actions,
            state_space = env.n_states,
            seed = 10
        )


        if lg == "old":
            simlog = SMLR(file_name = None, task = task, participant_id = "test-agent")
        elif lg == "newer":
            simlog = SimulationLoggerNew(file_name = None, task = task, participant_id = "test-agent")
            simlog.categories_dict['total_reward'].mode = LogMode.EVENT

        simlog.create()
        env.setup(logger = simlog, window = None, expose_last_stim = True)
        df, _, _ = pspy_run_task(env, logger = simlog, agent = agent, random_state=10)

        df_out.append(pd.DataFrame(df.close()))

    print("done")


    df_out[1] = df_out[1][df_out[0].columns]
    df_out[1] = df_out[1].replace(to_replace=['None'], value="n/a")
    df_out[1].loc[:, "task"] = task

    assert (df_out[1] == df_out[0]).mean().mean() > 0.9999