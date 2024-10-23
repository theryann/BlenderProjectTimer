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

INACTIVE_TIMEOUT: int = 60 * 3      # seconds before counted as inactive (3 minutes)
TIMER_UPDATE_INTERVAL: int = 1             # number of seconds between checking if still working (=active)
SAVE_INTERVAL: int  = 10            # "activities" can occurr very fast in succession. It suffices to save in time intervalls (seconds) defined by this constants

session_start_epoch: int            # epoch second when "session" was started (only resets after inactivity) 
sprint_start_epoch: int = None      # epoch second to begin counting from (resets after each check-intervall)
last_activity_epoch: int = None     # timestamp of last activity in epoch seconds

session_time_s: int = None          # total time spend in project since opening file (minus inactivity) (only for display needed, not for logging)

currently_active: bool = None

LOG_FILE_NAME: str = 'log.json'
blend_file_name: str = None
blend_file_dir: str = None

def save_working_time_to_json() -> None:
    """ load log file, add new elapsed time and save """
    global sprint_start_epoch, last_activity_epoch, session_start_epoch
    global blend_file_name, blend_file_dir, LOG_FILE_NAME
    global currently_active

    # abort if currently inactive (else the counter would increase while actually inactive)
    if not currently_active:
        return SAVE_INTERVAL
    
    # abort if no filename/directoryname is known (where should it even be saved?)
    # the reasons for this is that the blendfile is not saved yet
    if not blend_file_name:
        return SAVE_INTERVAL

    log_file_path: str = os.path.join( blend_file_dir, LOG_FILE_NAME )
    log_file: dict = None

    # create logfile if not existis
    if not os.path.exists( log_file_path ):
        with open( log_file_path, 'w' ) as fp:
            json.dump({
                "total_minutes": 0,
                "individual_files": {},
                "all_sprints": []
            },
            fp, indent=4)
    
    # load logfile
    with open( log_file_path, 'r' ) as fp:
        log_file = json.load( fp )

    elapsed_time_s: int = last_activity_epoch - sprint_start_epoch

    if elapsed_time_s == 0:
        return SAVE_INTERVAL

    elapsed_time_minutes: int = elapsed_time_s / 60
    begin_string: str = time.strftime('%FT%H:%M:%S', time.localtime( sprint_start_epoch ))
    end_string: str   = time.strftime('%FT%H:%M:%S', time.localtime( sprint_start_epoch + elapsed_time_s ))

    # update currents sprint elapsed time if it's already recorded
    # "sprint recorded" means the begin_string is in the list of sprints
    curr_sprint_found: bool = False 
    
    for i, sprint in enumerate(log_file["all_sprints"]):
        if not sprint.get("file") == blend_file_name:
            continue
        if not sprint.get("starttime") == begin_string:
            continue

        # begin_string found => so replace time elapsed
        log_file["all_sprints"][i]["endtime"] = end_string
        log_file["all_sprints"][i]["minutes_elapsed"] = elapsed_time_minutes

        curr_sprint_found = True
        break

    # add current sprint to list of all sprints since it's not recorded yet
    if not curr_sprint_found:
        log_file["all_sprints"].append({
            "file": blend_file_name,
            "starttime": begin_string,
            "endtime": end_string,
            "minutes_elapsed": elapsed_time_minutes
        })

    # add elapsed time to counter of this blend file
    # and sum all files to new total time
    # calculate this from the list of sprint (because this save function is called periodically i can not just add to the counter)
    sum_sprints_durations_min: float = sum([
        sess.get("minutes_elapsed")
        for sess in log_file["all_sprints"]
        if sess["file"] == blend_file_name
    ])
    log_file["individual_files"][blend_file_name] = sum_sprints_durations_min

    log_file["total_minutes"] = sum( log_file.get("individual_files").values() )
    
    # save updated file
    with open( log_file_path, 'w' ) as fp:
        json.dump( log_file, fp, indent=4 )

    return SAVE_INTERVAL

def update_timer() -> int:
    """
    gets called every x seconds (TIMER_UPDATE_INTERVAL)
    and updates the time variables, the inactivity state and calls for the saving of the logfile
    @return: the number of seconds until next call of this function 
    """
    global TIMER_UPDATE_INTERVAL, INACTIVE_TIMEOUT, currently_active
    global last_activity_epoch, sprint_start_epoch, session_time_s

    # fetch current time as epoch timestamp on seoconds
    current_time_s: int = int( time.time() )

    # if inactive nothing needs to be updated
    if not currently_active:
        return TIMER_UPDATE_INTERVAL
    
    # use the current time for session timer (the UI element) since it also counts as active time
    # (inactivity returns this function earlier)
    session_time_s = current_time_s - session_start_epoch 

    # if active but time of inactivity longer than timeout set to inactive
    if current_time_s - last_activity_epoch > INACTIVE_TIMEOUT:
        currently_active = False
        last_activity_epoch = None
        sprint_start_epoch = None
        return TIMER_UPDATE_INTERVAL
    
    return TIMER_UPDATE_INTERVAL

def track_activity(context) -> None:
    """
    is called when an event happens
    resets the last_activity_epoch time
    """
    global last_activity_epoch, currently_active, sprint_start_epoch, session_start_epoch

    # reset last_activity time
    previous_activity_epoch: int = last_activity_epoch

    current_time_s = int( time.time() )
    last_activity_epoch = current_time_s

    # if officially in inactive state, set to active
    if not currently_active:
        currently_active = True
        sprint_start_epoch = current_time_s # start new sprint

def ui_draw_elapsed_time(self, context) -> None:
    """draws the currently elapsed time to the Blender UI"""
    global session_time_s

    if session_time_s < 3600:
        minutes, seconds = divmod(session_time_s, 60)
        self.layout.label(text=f"{minutes:02}min {seconds:02}s")
    else:
        hours, seconds = divmod(session_time_s, 3600)
        self.layout.label(text=f"{hours}h { seconds // 60 :02}min")

def register():
    global sprint_start_epoch, session_time_s, last_activity_epoch, currently_active, session_start_epoch
    global blend_file_name, blend_file_dir

    # add timer to 3D view
    bpy.types.VIEW3D_HT_header.append( ui_draw_elapsed_time )

    # add blender internal timer to repeatedly call the update functions
    bpy.app.timers.register( update_timer )
    bpy.app.timers.register( save_working_time_to_json )

    # initalize time variables
    curr_time: int = int( time.time() )

    session_start_epoch = curr_time
    sprint_start_epoch  = curr_time
    last_activity_epoch = curr_time
    session_time_s = 0
    currently_active = True

    blend_file_path: str = bpy.data.filepath

    if blend_file_path:
        blend_file_dir  = os.path.dirname(  blend_file_path )
        blend_file_name = os.path.basename( blend_file_path )
    
    # track the user input events to track the activity
    bpy.app.handlers.depsgraph_update_post.append( track_activity )

def unregister():
    bpy.types.VIEW3D_HT_header.remove( ui_draw_elapsed_time )
    bpy.app.timers.unregister( update_timer )
    bpy.app.timers.unregister( save_working_time_to_json )
    bpy.app.handlers.depsgraph_update_post.remove( track_activity )

if __name__ == '__main__':
    try:
        unregister()
    except Exception as e:
        print('unregistering failed', e)
    register()