from firebase import sprints_ref

def sync_task_in_sprint(project_id: str, sprint_id: str, old_user_story_id: str, new_user_story_id: str, task_id: str):
    sprint_query = sprints_ref\
        .where("id", "==", sprint_id)\
        .where("project_id", "==", project_id)\
        .limit(1).stream()
    sprint_list = list(sprint_query)
    if sprint_list:
        sprint_ref = sprints_ref.document(sprint_list[0].id)
        sprint_doc = sprint_ref.get().to_dict()
        us_list = sprint_doc.get("user_stories", [])
        for us in us_list:
            # Quita de la user story vieja
            if old_user_story_id and us.get("id") == old_user_story_id and "tasks" in us:
                if task_id in us["tasks"]:
                    us["tasks"].remove(task_id)
            # Agrega a la user story nueva
            if new_user_story_id and us.get("id") == new_user_story_id and "tasks" in us:
                if task_id not in us["tasks"]:
                    us["tasks"].append(task_id)
        sprint_ref.update({
            "user_stories": us_list
        })
