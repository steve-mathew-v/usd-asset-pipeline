"""One-time installer for the Maya pipeline tools.

Run this from Maya's script editor (or drag it into the viewport):

    import install
    install.run()

It adds the pipeline to Maya's userSetup.py so the module is always
importable, then builds the OBJPipeline shelf.
"""

import os

import maya.cmds as cmds

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")


def _add_to_user_setup() -> None:
    """Append our sys.path line to userSetup.py if it is not already there."""
    scripts_dir = cmds.internalVar(userScriptDir=True)
    user_setup = os.path.join(scripts_dir, "userSetup.py")
    line = f"import sys; sys.path.append(r'{PIPELINE_DIR}')\n"

    if os.path.exists(user_setup):
        with open(user_setup) as setup_file:
            if PIPELINE_DIR in setup_file.read():
                print("already in userSetup.py")
                return

    with open(user_setup, "a") as setup_file:
        setup_file.write(line)
    print(f"added pipeline path to {user_setup}")


def run() -> None:
    """Install the pipeline: update userSetup.py and build the shelf."""
    _add_to_user_setup()

    import sys

    if PIPELINE_DIR not in sys.path:
        sys.path.append(PIPELINE_DIR)

    import pipeline

    pipeline.setup_shelf()

    cmds.confirmDialog(
        title="OBJ Pipeline",
        message="Installed. Use the OBJPipeline shelf to get started.",
        button=["OK"],
    )


if __name__ == "__main__":
    run()
