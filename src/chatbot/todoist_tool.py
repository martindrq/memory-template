import logging
import os
import requests
from datetime import datetime, timedelta
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from todoist_api_python.api import TodoistAPI
from todoist_api_python.api_async import TodoistAPIAsync
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import json
import dataclasses
logger = logging.getLogger("todoist_tool")

api = TodoistAPI(os.environ.get("TODOIST_API_KEY"))
api_sync = TodoistAPIAsync(os.environ.get("TODOIST_API_KEY"))

class Task(BaseModel):
    task_id: Optional[str] = Field(description="Task ID in case of update.")
    content: str = Field(
        description="Task content. This value may contain markdown-formatted text and hyperlinks. Details on markdown support can be found in the Text Formatting article in the Help Center."
    )
    description: str = Field(
        description="A description for the task. This value may contain markdown-formatted text and hyperlinks. Details on markdown support can be found in the Text Formatting article in the Help Center."
    )
    priority: int = Field(
        description="Task priority from 1 (normal, default value) to 4 (urgent)."
    )
    due_date: str = Field(description="Due date in YYYY-MM-DD format, corrected to user's timezone.")
    due_is_recurring: bool = Field(description="Flag indicating if the due date is recurring.")
    due_string: str = Field(description="Human-defined due date in arbitrary format.")

@tool(args_schema=Task)
def add_or_update_task(task_id: str, content: str, description: str, priority: int, due_date:str, due_is_recurring: bool, due_string: str):
    """Call to add or update a user task."""
    try:
        if(task_id):
            task = api.update_task(
                task_id=task_id, 
                content=content, 
                description=description, 
                order=order, 
                priority=priority,
                due_string=due_string,
                due_date=due_date,
                due_is_recurring=due_is_recurring)
            return f"Task {task_id} has been updated successfully.",
            
        else:
            task = api.add_task(
                content=content, 
                description=description, 
                order=order, 
                priority=priority,
                due_string=due_string,
                due_date=due_date,
                due_is_recurring=due_is_recurring)
            return f"Task {task.id} has been added successfully"

    except Exception as error:
        return f"Error updating task: {str(error)}"
    
@tool
def close_a_task(task_id: str):
    """Call to mark a task as completed."""
    try:
        api.close_task(task_id=task_id)
        return f"Task {task_id} has been closed.",
    except Exception as error:
        return f"Error closing task: {str(error)}"
    
@tool
def get_completed_tasks():
    """Call to get the completed tasks of today."""
    try:
        # remove one day
        yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        url = "https://api.todoist.com/sync/v9/activity/get"
        token = os.environ.get("TODOIST_API_KEY")
        headers = {
            "Authorization": f"Bearer {token}",  
            "Content-Type": "application/json"
        }
        params = {
            "limit": 100, 
            "event_type": "completed"
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        completed_today = []
        for event in data.get("events", []):
            event_date = event.get("event_date", "")
            logger.info(f"event_date {event_date} {yesterday_str}")
            if event_date.startswith(yesterday_str):
                logger.info(f"event_date {event_date} today")
                task_info = {
                    "content": event["extra_data"].get("content", ""),
                    "event_date": event_date,
                    "project_id": event.get("parent_project_id", ""),
                }
                completed_today.append(task_info)
        logger.info(f"Completed {completed_today}")
        return f"Completed tasks: {completed_today}"
    except Exception as error:
        logger.error(f"Error getting completed tasks: {str(error)}")
        return f"Error closing task: {str(error)}"
 

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

tasks_tools = [add_or_update_task, close_a_task, get_completed_tasks]
tasks_tools_node = ToolNode(tasks_tools)
