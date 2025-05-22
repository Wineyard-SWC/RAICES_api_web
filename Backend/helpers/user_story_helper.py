from firebase import userstories_ref, tasks_ref, sprints_ref, bugs_ref

def remove_task_from_user_story(project_id: str, user_story_id: str, task_id: str, task_points: int, was_done: bool):
    us_query = userstories_ref\
        .where("uuid", "==", user_story_id)\
        .where("projectRef", "==", project_id)\
        .limit(1).stream()
    us_list = list(us_query)

    if us_list:
        us_ref = userstories_ref.document(us_list[0].id)
        us_doc = us_ref.get().to_dict()
        task_list = us_doc.get("task_list", [])
        if task_id in task_list:
            task_list.remove(task_id)
        total_tasks = max((us_doc.get("total_tasks") or 1) - 1, 0)
        task_completed = us_doc.get("task_completed") or 0
        points = max((us_doc.get("points") or 0) - (task_points or 0), 0)
        if was_done:
            task_completed = max(task_completed - 1, 0)
        us_ref.update({
            "task_list": task_list,
            "total_tasks": total_tasks,
            "task_completed": task_completed,
            "points": points
        })

def add_task_to_user_story(project_id: str, user_story_id: str, task_id: str, task_points: int, is_done: bool):
    us_query = userstories_ref\
        .where("uuid", "==", user_story_id)\
        .where("projectRef", "==", project_id)\
        .limit(1).stream()
    us_list = list(us_query)

    if us_list:
        us_ref = userstories_ref.document(us_list[0].id)
        us_doc = us_ref.get().to_dict()
        task_list = us_doc.get("task_list", [])
        if task_id not in task_list:
            task_list.append(task_id)
        total_tasks = (us_doc.get("total_tasks") or 0) + 1
        task_completed = us_doc.get("task_completed") or 0
        points = (us_doc.get("points") or 0) + (task_points or 0)
        if is_done:
            task_completed += 1
        us_ref.update({
            "task_list": task_list,
            "total_tasks": total_tasks,
            "task_completed": task_completed,
            "points": points
        })



def delete_user_story_and_related(project_id: str, story_id: str):
    # Obtener el documento por su ID
    story_doc_ref = userstories_ref.document(story_id)
    story_doc = story_doc_ref.get()

    if not story_doc.exists:
        raise Exception("User story not found")

    story_data = story_doc.to_dict()
    user_story_uuid = story_data.get("uuid")
    task_list = story_data.get("task_list", [])

    # Borrar las tareas relacionadas
    for task_id in task_list: 
        tasks_ref.document(task_id).delete()

    # Borrar bugs relacionados por user_story_uuid
    bugs_query = bugs_ref.where("userStoryRelated", "==", user_story_uuid).where("projectId", "==", project_id).stream()
    for bug in bugs_query:
        bugs_ref.document(bug.id).delete()

    # Quitar user story de todos los sprints
    sprints = sprints_ref.where("project_id", "==", project_id).stream()
    for sprint in sprints:
        sprint_doc = sprint.to_dict()
        us_list = sprint_doc.get("user_stories", [])

        new_us_list = [us for us in us_list if us.get("id") != user_story_uuid]
        
        if len(new_us_list) != len(us_list):  
            sprints_ref.document(sprint.id).update({"user_stories": new_us_list})

    # Borrar el user story
    story_doc_ref.delete()

        

    
