import os
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from todoist_api_python.api import TodoistAPI
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import json

api = TodoistAPI(os.environ.get("TODOIST_API_KEY"))

class Task(BaseModel):
    task_id: Optional[str] = Field(description="Task ID in case of update.")
    project_id: str = Field(description="Task's project ID.")
    content: str = Field(
        description="Task content. This value may contain markdown-formatted text and hyperlinks. Details on markdown support can be found in the Text Formatting article in the Help Center."
    )
    description: str = Field(
        description="A description for the task. This value may contain markdown-formatted text and hyperlinks. Details on markdown support can be found in the Text Formatting article in the Help Center."
    )
    is_completed: bool = Field(description="Flag to mark completed tasks.")
    labels: List[str] = Field(
        description="The task's labels (a list of names that may represent either personal or shared labels)."
    )
    order: int = Field(
        description="Position under the same parent or project for top-level tasks (read-only)."
    )
    priority: int = Field(
        description="Task priority from 1 (normal, default value) to 4 (urgent)."
    )
    due_date: str = Field(description="Due date in YYYY-MM-DD format, corrected to user's timezone.")
    due_is_recurring: bool = Field(description="Flag indicating if the due date is recurring.")
    due_string: str = Field(description="Human-defined due date in arbitrary format.")

@tool(args_schema=Task)
def add_or_update_task(task_id: str, project_id: str, content: str, description: str, is_completed: bool, labels: List[str], order: int, priority: int, due_date:str, due_is_recurring: bool, due_string: str):
    """Call to add or update a user task."""
    try:
        if(task_id):
            task = api.update_task(
                task_id=task_id, 
                content=content, 
                description=description, 
                is_completed=is_completed, 
                labels=labels, 
                order=order, 
                priority=priority,
                due_string=due_string,
                due_date=due_date,
                due_is_recurring=due_is_recurring)
            return f"Task {task_id} has been updated successfully.",
            
        else:
            task = api.add_task(
                project_id=project_id, 
                content=content, 
                description=description, 
                is_completed=is_completed, 
                labels=labels, 
                order=order, 
                priority=priority,
                due_string=due_string,
                due_date=due_date,
                due_is_recurring=due_is_recurring)
            return f"Task {task.id} has been added successfully"

    except Exception as error:
        return f"Error updating task: {str(error)}"
 

def get_tasks(workspace:str):
    try:
        filter=f"workspace:{workspace}"
        if(workspace != "Work"):
            filter = f"!workspace:Work"
        tasks = api.get_tasks(filter=filter)
        tasks_list = []
        for task in tasks:
            # get the task project
            task_project = api.get_project(task.project_id)
            task.project_name = task_project.name
            tasks_list.append({
                "id": task.id,
                "content": task.content,
                "description": task.description,
                "is_completed": task.is_completed,
                "labels": task.labels,
                "order": task.order,
                "priority": task.priority,
                "project_name": task.project_name,
                "due": { 
                    "date": task.due.date, 
                    "is_recurring":  task.due.is_recurring,
                    "string": task.due.string,
                } if task.due else None
            })
        # return a string separated by break lines
        return "\n".join([json.dumps(task) for task in tasks_list])
    except Exception as error:
        return f"Error getting tasks: {str(error)}"

tasks_tools = [add_or_update_task]
tasks_tools_node = ToolNode(tasks_tools)