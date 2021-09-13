import requests
import urllib
from urllib.parse import urlparse
import os
import json
import ntpath
from clickupy import helpers
from clickupy import folder
from clickupy import clickuplist
from clickupy import attachment
from clickupy import exceptions
from clickupy import comment
from clickupy import task
from typing import List
from clickupy.helpers.timefuncs import fuzzy_time_to_seconds, fuzzy_time_to_unix
from clickupy.helpers import formatting


API_URL = 'https://api.clickup.com/api/v2/'


class ClickUpClient():

    def __init__(self, accesstoken: str, api_url: str = API_URL):
        self.api_url = api_url
        self.accesstoken = accesstoken

    def __headers(self, file_upload: bool = False):

        if file_upload:
            headers = {'Authorization': self.accesstoken}
        else:
            headers = {'Authorization': self.accesstoken,
                       'Content-Type':  'application/json'}
        return headers

    # Performs a Get request to the ClickUp API
    def __get_request(self, model, *additionalpath):

        path = formatting.url_join(API_URL, model, *additionalpath)
        response = requests.get(path, headers=self.__headers())
        response_json = response.json()
        if response.status_code == 429:
            raise exceptions.ClickupClientError(
                "Rate limit exceeded", response.status_code)
        if response.status_code in [401, 400]:
            raise exceptions.ClickupClientError(
                response_json['err'], response.status_code)
        if response.ok:
            return response_json

    # Performs a Post request to the ClickUp API
    def __post_request(self, model, data, upload_files=None, file_upload=False, *additionalpath):
        path = formatting.url_join(API_URL, model, *additionalpath)

        if upload_files:
            response = requests.post(path, headers=self.__headers(
                True), data=data, files=upload_files)
        else:
            response = requests.post(
                path, headers=self.__headers(), data=data)
        response_json = response.json()

        # TODO #11 Update this to list
        if response.status_code == 401 or response.status_code == 400 or response.status_code == 500:
            raise exceptions.ClickupClientError(
                response_json['err'], response.status_code)
        if response.ok:
            return response_json

    # Performs a Put request to the ClickUp API
    def __put_request(self, model, data, *additionalpath):
        path = formatting.url_join(API_URL, model, *additionalpath)
        response = requests.put(path, headers=self.__headers(), data=data)
        response_json = response.json()
        if response.status_code == 401 or response.status_code == 400:
            raise exceptions.ClickupClientError(
                response_json['err'], response.status_code)
        if response.ok:
            return response_json

    # Performs a Delete request to the ClickUp API
    def __delete_request(self, model, *additionalpath):
        path = formatting.url_join(API_URL, model, *additionalpath)
        response = requests.delete(path, headers=self.__headers())
        if response.ok:
            return response.status_code
        else:
            raise exceptions.ClickupClientError(
                response_json['err'], response.status_code)

    def get_list(self, list_id: str) -> clickuplist.SingleList:
        """Fetches a single list item from a given list id and returns a List object.

        Args:
            list_id (str): The ID od the ClickUp list to be returned.

        Returns:
            clickuplist.SingleList: Returns a list of type List.
        """
        model = "list/"
        fetched_list = self.__get_request(model, list_id)

        return clickuplist.SingleList.build_list(fetched_list)

    def get_lists(self, folder_id: str) -> clickuplist.AllLists:
        """Fetches all lists from a given folder id and returns a list of List objects.

        Args:
            folder_id (str): The ID od the ClickUp folder to be returned.

        Returns:
            list.AllLists: Returns a list of type AllLists.
        """
        model = "folder/"
        fetched_lists = self.__get_request(model, folder_id)
        final_lists = clickuplist.AllLists.build_lists(fetched_lists)
        return final_lists

    # Creates and returns a List object in a folder from a given folder ID
    def create_list(self, folder_id: str, name: str, content: str, due_date: str, priority: int, status: str) -> clickuplist.SingleList:
        """Creates and returns a List object in a folder from a given folder ID.

        Args:
            folder_id (str): The ID of the ClickUp folder.
            name (str): The name of the created list.
            content (str): The description content of the created list.
            due_date (str): The due date of the created list.
            priority (int): An integer 1 : Urgent, 2 : High, 3 : Normal, 4 : Low.
            status (str): Refers to the List color rather than the task Statuses available in the List.

        Returns:
            list.SingleList: Returns an object of type SingleList.
        """
        data = {
            'name': name,
            'content': content,
            'due_date': due_date,
            'status': status
        }
        model = "folder/"
        created_list = self.__post_request(
            model, json.dumps(data), None, False, folder_id, "list")
        if created_list:
            final_list = clickuplist.SingleList.build_list(created_list)
            return final_list

    def get_folder(self, folder_id: str) -> folder.Folder:
        """Fetches a single folder item from a given folder id and returns a Folder object.

        Args:
            folder_id (str): The ID of the ClickUp folder to retrieve.

        Returns:
            Folder: Returns an object of type Folder.
        """
        model = "folder/"
        fetched_folder = self.__get_request(model, folder_id)
        if fetched_folder:
            final_folder = folder.Folder.build_folder(fetched_folder)
            return final_folder

    def get_folders(self, space_id: str) -> folder.Folders:
        """Fetches all folders from a given space ID and returns a list of Folder objects.

        Args:
            space_id (str): The ID of the ClickUp space to retrieve the list of folder from.

        Returns:
            Folders: Returns a list of Folder objects.
        """
        model = "space/"
        fetched_folders = self.__get_request(model, space_id, "folder")
        if fetched_folders:
            final_folders = folder.Folders.build_folders(fetched_folders)
            return final_folders

    def create_folder(self, space_id: str, name: str) -> folder.Folder:
        """Creates and returns a Folder object in a space from a given space ID.

        Args:
            space_id (str): The ID of the ClickUp space to create the folder inside.
            name (str): String value that the created folder will utilize as its name.

        Returns:
            Folder: Returns the created Folder object.
        """
        data = {
            'name': name,
        }
        model = "space/"
        created_folder = self.__post_request(
            model, json.dumps(data), None, False, space_id,  "folder")
        if created_folder:
            final_folder = folder.Folder.build_folder(created_folder)
            return final_folder

    def update_folder(self, folder_id: str, name: str) -> folder.Folder:
        """Updates the name of a folder given the folder ID.

        Args:
            folder_id (str): The ID of the ClickUp folder to update.
            name (str): String that the folder name will be updated to reflect.

        Returns:
            Folder: Returns the updated Folder as an object.
        """
        data = {
            'name': name,
        }
        model = "folder/"
        updated_folder = self.__put_request(
            model, json.dumps(data), folder_id)
        if updated_folder:
            final_folder = folder.Folder.build_folder(updated_folder)
            return final_folder

    def delete_folder(self, folder_id: str) -> None:
        """Deletes a folder from a given folder ID.

        Args:
            folder_id (str): The ID of the ClickUp folder to delete.
        """
        model = "folder/"
        deleted_folder_status = self.__delete_request(
            model, folder_id)
        return(True)

    # Tasks

    def upload_attachment(self, task_id: str, file_path: str) -> attachment.Attachment:
        """Uploads an attachment to a ClickUp task.

        Args:
            task_id (str): The ID of the task to upload to.
            file_path (str): The filepath of the file to upload.

        Returns:
            Attachment: Returns an attachment object.
        """

        if os.path.exists(file_path):

            f = open(file_path, 'rb')
            files = [
                ('attachment', (f.name, open(
                    file_path, 'rb')))
            ]
            data = {'filename': ntpath.basename(f.name)}
            model = "task/" + task_id
            uploaded_attachment = self.__post_request(
                model, data, files, True, "attachment")

            if uploaded_attachment:
                final_attachment = attachment.build_attachment(
                    uploaded_attachment)
            return final_attachment

    def get_task(self, task_id: str) -> task.Task:
        """Fetches a single ClickUp task item and returns a Task object.

        Args:
            task_id (str): The ID of the task to return.

        Returns:
            Task: Returns an object of type Task.
        """
        model = "task/"
        fetched_task = self.__get_request(model, task_id)
        final_task = task.Task.build_task(fetched_task)
        if final_task:
            return final_task

    def get_tasks(self, list_id: str) -> task.Tasks:
        """Fetches a list of task items from a given list ID.

        Args:
            list_id (str): The ID of the ClickUp list to fetch tasks from.

        Returns:
            task.Tasks: Returns an object of type Tasks.
        """
        model = "list/"
        fetched_tasks = self.__get_request(model, list_id, "task")

        return task.Tasks.build_tasks(fetched_tasks)

    def create_task(self, list_id: str, name: str, description: str = None, priority: int = None, assignees: [] = None, tags: [] = None,
                    status: str = None, due_date: str = None, start_date: str = None, notify_all: bool = True) -> task.Task:

        if priority and priority not in range(1, 4):
            raise exceptions.ClickupClientError(
                "Priority must be in range of 0-4.", "Priority out of range")
        if due_date:
            due_date = fuzzy_time_to_unix(due_date)

        arguments = {}
        arguments.update(vars())
        arguments.pop('self', None)
        arguments.pop('arguments', None)
        arguments.pop('list_id', None)

        final_dict = json.dumps(
            {k: v for k, v in arguments.items() if v is not None})

        model = "list/"
        created_task = self.__post_request(
            model, final_dict, None, False, list_id,  "task")

        if created_task:
            return task.Task.build_task(created_task)

    def update_task(self, task_id, name: str = None, description: str = None, status: str = None, priority: int = None, time_estimate: int = None,
                    archived: bool = None, add_assignees: List[str] = None, remove_assignees: List[int] = None) -> task.Task:
        """[summary]

        Args:
            task_id ([type]): The ID of the ClickUp task to update.
            name (str, optional): Sting value to update the task name to. Defaults to None.
            description (str, optional): Sting value to update the task description to. Defaults to None.
            status (str, optional): String value of the tasks status. Defaults to None.
            priority (int, optional): Priority of the task. Range 1-4. Defaults to None.
            time_estimate (int, optional): Time estimate of the task. Defaults to None.
            archived (bool, optional): Whether the task should be archived or not. Defaults to None.
            add_assignees (List[str], optional): List of assignee IDs to add to the task. Defaults to None.
            remove_assignees (List[int], optional): List of assignee IDs to remove from the task. Defaults to None.

        Raises:
            exceptions.ClickupClientError: Raises "Priority out of range" exception for invalid priority range.

        Returns:
            task.Task: Returns an object of type Task.
        """
        if priority and priority not in range(1, 4):
            raise exceptions.ClickupClientError(
                "Priority must be in range of 0-4.", "Priority out of range")

        arguments = {}
        arguments.update(vars())
        arguments.pop('self', None)
        arguments.pop('arguments', None)
        arguments.pop('task_id', None)
        arguments.pop('add_assignees', None)
        arguments.pop('remove_assignees', None)

        if add_assignees and remove_assignees:
            arguments.update(
                {'assignees': {'add': add_assignees, 'rem': remove_assignees}})
        elif add_assignees:
            arguments.update({'assignees': {'add': add_assignees}})
        elif remove_assignees:
            arguments.update({'assignees': {'rem': remove_assignees}})

        final_dict = json.dumps(
            {k: v for k, v in arguments.items() if v is not None})

        model = "task/"
        updated_task = self.__put_request(
            model, final_dict, task_id)
        if updated_task:
            return task.Task.build_task(updated_task)

    def delete_task(self, task_id: str) -> None:
        """Deletes a task from a given task ID.

        Args:
            folder_id (str): The ID of the ClickUp task to delete.
        """
        model = "task/"
        deleted_task_status = self.__delete_request(
            model, task_id)
        return(True)

    # Comments
    def get_task_comments(self, task_id: str):

        model = "task/"
        fetched_comments = self.__get_request(model, task_id, "comment")
        final_comments = comment.Comments.build_comments(fetched_comments)
        if final_comments:
            return final_comments

    def get_list_comments(self, list_id: str):

        model = "list/"
        fetched_comments = self.__get_request(model, list_id, "comment")
        final_comments = comment.Comments.build_comments(fetched_comments)
        if final_comments:
            return final_comments

    def get_chat_comments(self, view_id: str):

        model = "view/"
        fetched_comments = self.__get_request(model, view_id, "comment")
        final_comments = comment.Comments.build_comments(fetched_comments)
        if final_comments:
            return final_comments

    def update_comment(self, comment_id: str, comment_text: str = None, assignee: str = None, resolved: bool = None) -> comment.Comment:

        arguments = {}
        arguments.update(vars())
        arguments.pop('self', None)
        arguments.pop('arguments', None)
        arguments.pop('comment_id', None)

        model = "comment/"

        final_dict = json.dumps(
            {k: v for k, v in arguments.items() if v is not None})

        updated_comment = self.__put_request(
            model, final_dict, comment_id)
        if updated_comment:
            return True

    def delete_comment(self, comment_id: str) -> bool:

        model = "comment/"
        deleted_comment_status = self.__delete_request(
            model, comment_id)
        return(True)

    def create_task_comment(self, task_id: str, comment_text: str, assignee: str = None, notify_all: bool = True) -> comment.Comment:

        arguments = {}
        arguments.update(vars())
        arguments.pop('self', None)
        arguments.pop('arguments', None)
        arguments.pop('task_id', None)

        model = "task/"

        final_dict = json.dumps(
            {k: v for k, v in arguments.items() if v is not None})

        created_comment = self.__post_request(
            model, final_dict, None, False, task_id, "comment")

        final_comment = comment.Comment.build_comment(created_comment)
        if final_comment:
            return final_comment
