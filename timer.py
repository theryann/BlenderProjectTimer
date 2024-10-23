bl_info = {
    "name": "Blender Project Timer",
    "author": "Darian Patzak",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Info",
    "description": "Log and display time spend on Blender Projects in this directory",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Interface"
}

import bpy
import json
import time
import os

INACTIVE_TIMEOUT: int = 60 * 3      # 3 minutes before counted as inactive
CHECK_INTERVAL: int = 10            # 10 seconds between checking if still working

start_time_s: int = None            # start timestamp in epoch seconds to begin counting from (resets after each check-intervall)
last_activity_s: int = None         # timestamp of last activity in epoch seconds

total_time_s: int = None            # total time spend in project since opening file (minus inactivity)

currently_active: bool = None

LOG_FILE_NAME: str = 'log.json'
blend_file_name: str = None
blend_file_dir: str = None

def save_working_time_to_json() -> None:
    """ load log file, add new elapsed time and save """
    global start_time_s, last_activity_s
    global blend_file_name, blend_file_dir, LOG_FILE_NAME
    global currently_active

    # abort if currently inactive (else the counter would increase while actually inactive)
    if not currently_active:
        return
    
    # abort if no filename/directoryname is known (where should it even be saved?)
    # this means the blendfile is not saved yet
    if not blend_file_name:
        return

    log_file_path: str = os.path.join( blend_file_dir, LOG_FILE_NAME )
    log_file: dict = None

    # create logfile if not existis
    if not os.path.exists( log_file_path ):
        with open( log_file_path, 'w' ) as fp:
            json.dump({
                "total_minutes": 0,
                "individual_files": {},
                "all_sessions": []
            },
            fp, indent=4)
    
    # load logfile
    with open( log_file_path, 'r' ) as fp:
        log_file = json.load( log_file_path )

    elapsed_time_s: int = last_activity_s - start_time_s
    begin_string: str = time.strftime('%FT%H:%M:%S', time.localtime( start_time_s ))
    end_string: str   = time.strftime('%FT%H:%M:%S', time.localtime( start_time_s + elapsed_time_s ))

    # update currents session elapsed time if it's already recorded
    # "session recorded" means the begin_string
    curr_session_found = False
    
    for i, session in enumerate(log_file["all_sessions"]):
        if not session.get("file") == blend_file_name:
            continue
        if not session.get("starttime") == begin_string:
            continue

        # begin_string found => so replace time elapsed
        log_file["all_sessions"][i]["endtime"] = end_string
        log_file["all_sessions"][i]["minutes_elapsed"] = elapsed_time_s

        curr_session_found = True
        break

    # add current session to list of all sessions since it's not recorded yet
    if not curr_session_found:
        log_file["all_sessions"].append({
            "file": blend_file_name,
            "starttime": begin_string,
            "endtime": end_string,
            "minutes_elapsed": elapsed_time_s
        })

    # add elapsed time to counter of this blend file
    # and sum all files to new total time

    if blend_file_name in log_file.get("individual_files"):
        log_file["individual_files"][blend_file_name] += elapsed_time_s
    else:
        log_file["individual_files"][blend_file_name]  = elapsed_time_s
    
    log_file["total_minutes"] = sum( log_file.get("individual_files").values() )
    
    # save updated file
    with open( log_file_path, 'w' ) as fp:
        json.dump( log_file, fp, indent=4 )
    print('saved log:', log_file_path)

def update_timer() -> int:
    """
    gets called every x seconds (CHECK_INTERVAL)
    and updates the time variables, the inactivity state and calls for the saving of the logfile
    @return: the number of seconds until next call of this function 
    """
    global CHECK_INTERVAL, INACTIVE_TIMEOUT, currently_active
    global last_activity_s, start_time_s, total_time_s

    # fetch current time as epoch timestamp on seoconds
    current_time_s: int = int( time.time() )

    # if inactive nothing needs to be updated
    if not currently_active:
        return CHECK_INTERVAL
    
    total_time_s += last_activity_s - start_time_s
    print(total_time_s, currently_active)

    # if active but time of inactivity longer than timeout set to inactive
    if last_activity_s + current_time_s > INACTIVE_TIMEOUT:
        currently_active = False
        last_activity_s = None
        start_time_s = None
        return CHECK_INTERVAL
    
    start_time_s = current_time_s

    return CHECK_INTERVAL

def track_activity(context) -> None:
    """
    is called when an event happens
    resets the last_activity_s time
    """
    global last_activity_s, currently_active, start_time_s

    # reset last_activity time
    current_time_s = int( time.time() )
    last_activity_s = current_time_s
    
    # save timer state
    save_working_time_to_json()

    # if officially in inactive state, set to active
    if not currently_active:
        currently_active = True
        start_time_s = current_time_s

def ui_draw_elapsed_time(self, context) -> None:
    """draws the currently elapsed time to the Blender UI"""
    global total_time_s
    minutes, seconds = divmod(total_time_s, 60)
    self.layout.label(text=f"{minutes:2}:{seconds:2}")


def register():
    global start_time_s, total_time_s, last_activity_s, currently_active
    global blend_file_name, blend_file_dir

    # bpy.utils.register_class(TIME_OT_reset)

    # add timer to 3D view
    bpy.types.VIEW3D_HT_header.append( ui_draw_elapsed_time )

    # add blender internal timer to repeatedly call the update functions
    bpy.app.timers.register( update_timer )

    # initalize time variables
    start_time_s = int( time.time() )
    total_time_s = 0
    last_activity_s = start_time_s
    currently_active = True

    blend_file_path: str = bpy.data.filepath

    if blend_file_path:
        blend_file_dir  = os.path.dirname(  blend_file_path )
        blend_file_name = os.path.basename( blend_file_path )
    
    save_working_time_to_json()

    # track the user input events to track the activity
    bpy.app.handlers.depsgraph_update_post.append( track_activity )

def unregister():
    # bpy.utils.unregister_class(TIME_OT_reset)
    bpy.types.VIEW3D_HT_header.remove( ui_draw_elapsed_time )
    bpy.app.timers.unregister( update_timer )
    bpy.app.handlers.depsgraph_update_post.remove( track_activity )

if __name__ == '__main__':
    register()