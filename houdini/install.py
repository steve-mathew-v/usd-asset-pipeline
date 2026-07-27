"""One-time installer for the Houdini pipeline tools.

Run this from Houdini's Python Source Editor (Windows > Python Source Editor):

    import sys
    sys.path.append(r"path/to/obj-pipeline/houdini")
    import install
    install.run()

It builds an "OBJ Pipeline" shelf with one tool per action. If the shelf does
not appear, right-click a shelf tab > Shelves and tick "OBJ Pipeline".
"""

import os

import hou

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")

# (tool suffix, label, python call)
TOOLS = [
    ("pub", "PUB", "pipeline.publish()"),
    ("imp", "IMP", "pipeline.import_all_ready()"),
    ("chk", "CHK", "pipeline.get_ready()"),
    ("ver", "VER", "pipeline.import_version()"),
    ("ok", "OK", "pipeline.approve()"),
    ("no", "NO", "pipeline.unapprove()"),
]


def run() -> None:
    """Create (or refresh) the OBJ Pipeline shelf and its tools."""
    shelves = hou.shelves.shelves()
    if "obj_pipeline" in shelves:
        shelf = shelves["obj_pipeline"]
    else:
        shelf = hou.shelves.newShelf(name="obj_pipeline", label="OBJ Pipeline")

    existing_tools = hou.shelves.tools()
    tools = []
    for suffix, label, call in TOOLS:
        script = (
            f"import sys\n"
            f"sys.path.append(r'{PIPELINE_DIR}')\n"
            f"import pipeline\n"
            f"{call}"
        )
        tool_name = f"obj_pipeline_{suffix}"
        if tool_name in existing_tools:
            tool = existing_tools[tool_name]
            tool.setScript(script)
        else:
            tool = hou.shelves.newTool(
                name=tool_name,
                label=label,
                script=script,
                language=hou.scriptLanguage.Python,
            )
        tools.append(tool)

    shelf.setTools(tools)
    hou.ui.displayMessage(
        "Installed. Use the OBJ Pipeline shelf.\n"
        "If you don't see it, right-click a shelf tab > Shelves > tick 'OBJ Pipeline'."
    )


if __name__ == "__main__":
    run()
