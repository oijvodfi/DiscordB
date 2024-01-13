import discord
import subprocess
from discord.ext import commands
import os
from dotenv import load_dotenv
import re
import json
from mailings import send_tasks_email

load_dotenv()
TOKEN = os.getenv('TOKEN')
PREFIX = os.getenv('PREFIX')
ALLOWED_CHANNEL_ID = os.getenv('ALLOWED_CHANNEL_ID')

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

with open('config.json') as f:
    config = json.load(f)

users = config['users']
projects = config['projects']

@bot.event
async def on_ready():
    print("DiscoBot started | Looking tassty")

@bot.command()
async def mail(ctx):
    send_tasks_email()
    await ctx.send('Отчет отправлен на почту.')

@bot.command()
async def task(ctx):
    await ctx.send("Приветствую", view=MainView())

# ГЛАВНОЕ МЕНЮ


class MainView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Задачи', style=discord.ButtonStyle.primary)
    async def working_menu_button(self,
                          interaction: discord.Interaction,
                          button: discord.ui.button):
        await interaction.response.edit_message(
            content="Выберите действие",
            view=WorkingView())
        
    @discord.ui.button(label='Расширенные возможности', style=discord.ButtonStyle.green)
    async def basic_menu_button(self,
                          interaction: discord.Interaction,
                          button: discord.ui.button):
        await interaction.response.edit_message(
            content="Выберите действие",
            view=BasicView())
        
    @discord.ui.button(label='Тег-менеджер', style=discord.ButtonStyle.green)
    async def tag_management_menu_button(self,
                          interaction: discord.Interaction,
                          button: discord.ui.button):
        await interaction.response.edit_message(
            content="Выберите действие",
            view=TagManagementView())
        
# КНОПКИ ПОДТВЕРЖДЕНИЯ (Да/Нет)


class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='Да', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()

    @discord.ui.button(label='Нет', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()

# СОЗДАТЬ ЗАДАЧУ


class CreateTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Создать задачу',
                         row=0,
                         custom_id='create_task',
                         style=discord.ButtonStyle.success)
        self.task_description = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите название для задачи")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        self.task_description = message.content

        view = ConfirmView()
        await interaction.followup.send(
            'Хотите ли вы назначить эту задачу '
            'определенному пользователю?', view=view)
        await view.wait()

        if view.value:
            await interaction.followup.send("Выберите пользователя, которому хотите назначить задачу", view=SelectUserView(users, self))
        else:
            subprocess.run(["task", "add", self.task_description])
            await interaction.followup.send(
                f'Задача "{self.task_description}" создана.')

class UserSelect(discord.ui.Select):
    def __init__(self, users, button):
        options = [
            discord.SelectOption(label=user['name'], value=user['id'])
            for user in users
        ]
        super().__init__(placeholder='Выберите пользователя', options=options)
        self.button = button

    async def callback(self, interaction: discord.Interaction):
        user_id = self.values[0]
        # Находим пользователя по его ID
        user = next((user for user in users if user['id'] == user_id), None)
        if user is None:
            await interaction.response.send_message('Пользователь не найден.')
            return
        # Замена всех спец. символов и пробелов на подчеркивания
        user_tag = ''.join(e if e.isalnum() else '_' for e in user['tag'])
        subprocess.run(["task", "add", self.button.task_description, f"+{user_tag}"])
        await interaction.response.send_message(
            f'Задача "{self.button.task_description}" создана и назначена пользователю {user["name"]}.')

class SelectUserView(discord.ui.View):
    def __init__(self, users, button):
        super().__init__()
        self.add_item(UserSelect(users, button))
                    
# ЗАВЕРШИТЬ ЗАДАЧУ


class DoneTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Завершить задачу',
                         row=1,
                         custom_id='done_task',
                         style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Введите ID задачи для ЗАВЕРШЕНИЯ (неск. - через пробел)")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        task_ids = message.content.strip().split()

        for task_id in task_ids:
            try:
                subprocess.run(
                    ["task", task_id, "done"], check=True)
            except subprocess.CalledProcessError:
                await interaction.followup.send(
                    f'Не удалось завершить задачу{task_id}'
                    'Проверьте ID задачи.')

        await interaction.followup.send(
            f'Задача {", ".join(task_ids)} завершена.')

# УДАЛЕНИЕ ЗАДАЧ


class DeleteTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Удаление задач',
                         row=2, custom_id='delete_task',
                         style=discord.ButtonStyle.danger
                         )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Введите ID задачи для УДАЛЕНИЯ (неск. - через пробел)")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        task_id = message.content

        confirm_view = ConfirmView()
        await interaction.followup.send(
            f'Вы уверены, что хотите удалить задачу {task_id}?', view=confirm_view)
        await confirm_view.wait()
        if confirm_view.value:
            task_ids = task_id.split()
            for task in task_ids:
                subprocess.run(["task", "rc.confirmation=no", task, "delete"])
            await interaction.followup.send(
                f'Задачи {task_id} удалены.')
        else:
            await interaction.followup.send(
                f'Удаление задачи {task_id} отменено.')

# СПИСОК ВСЕХ ЗАДАЧ


class ListTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Все задачи проекта',
                         row=1,
                         custom_id='list_tasks',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
                task_list = subprocess.check_output(
                    ["task", "list"], stderr=subprocess.STDOUT)
                task_list = task_list.decode('utf-8')
                task_list = f'```\n{task_list}\n```'
                await interaction.response.send_message(
                    f'Здесь все задачи: {task_list}')
                
# МОИ ЗАДАЧИ


class MyTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Мои задачи',
                         row=0,
                         custom_id='my_tasks',
                         style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name
        user_tag = ''.join(e if e.isalnum() else '_' for e in user_name)
        tag_argument = "+{0}".format(user_tag)
        try:
            task_list = subprocess.check_output(
                ["task", tag_argument, "list"], stderr=subprocess.STDOUT)
            task_list = task_list.decode('utf-8')
            task_list = f'```\n{task_list}\n```'
            await interaction.response.send_message(
                f'Ваши задачи: {task_list}')
        except subprocess.CalledProcessError:
            await interaction.response.send_message(
                'У вас нет задач.')

# Выполненные задачи


class CompletedTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Выполненные задачи',
                         row=1,
                         custom_id='completed_tasks',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        try:
            completed_tasks = subprocess.check_output(
                ["task", "completed"], stderr=subprocess.STDOUT)
            completed_tasks = completed_tasks.decode('utf-8')
            if completed_tasks.strip() == '':
                await interaction.response.send_message(
                    'К сожалению, ещё нет выполненных задач')
            else:
                completed_tasks = f'```\n{completed_tasks}\n```'
                await interaction.response.send_message(
                    f'Все выполненные задачи: {completed_tasks}')
        except subprocess.CalledProcessError:
            await interaction.response.send_message(
                'Произошла ошибка при получении списка выполненных задач. Похоже, список пуст')

# Добавить в проект


class ProjectSelect(discord.ui.Select):
    def __init__(self, task_id):
        options = [discord.SelectOption(label=project) for project in projects]
        options.append(discord.SelectOption(label='Добавить новый проект'))
        super().__init__(placeholder='Выберите проект', options=options)
        self.task_id = task_id

    async def callback(self, interaction: discord.Interaction):
        selected_option = self.values[0]
        if selected_option == 'Добавить новый проект':
            await interaction.response.send_message("Введите название нового проекта")
            def check(m):
                return (
                    m.author.id == interaction.user.id
                    and m.channel.id == interaction.channel.id
                )
            message = await bot.wait_for('message', check=check)
            new_project = message.content
            projects.append(new_project)
            # Сохранение нового проекта в файл
            with open('config.json', 'w') as f:
                json.dump({'users': users, 'projects': projects}, f, indent=4)
            await interaction.followup.send(f'Проект "{new_project}" добавлен.')
            selected_option = new_project
        else:
            await interaction.response.send_message(f'Выбран проект "{selected_option}"')
        project_name = selected_option
        
        if project_name != 'Добавить новый проект':
            subprocess.run(["task", self.task_id, "modify", "project:"+project_name])
            await interaction.followup.send(
                f'Задача {self.task_id} отправлена в проект {project_name}.')

class ProjectView(discord.ui.View):
    def __init__(self, task_id):
        super().__init__()
        self.add_item(ProjectSelect(task_id))

class AddProjectButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Добавить в проект',
                         row=0,
                         custom_id='add_project',
                         style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Введите ID задачи")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        task_id = message.content
        await interaction.followup.send("Теперь выберите проект", view=ProjectView(task_id))

# Добавить тег


class AddTagButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Добавить тег',
                         row=0,
                         custom_id='add_tag',
                         style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Введите ID задачи и тег (через пробел)")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        task_id, tag = message.content.split()
        subprocess.run(["task", task_id, "modify", "+"+tag])
        await interaction.followup.send(
            f'Тег {tag} добавлен в задачу {task_id}.')

# Фильтр по проекту


class FilterByProjectButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Фильтр по проекту',
                         row=1,
                         custom_id='filter_by_project',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Введите интересующий проект")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        project_name = message.content.strip()

        try:
            task_list = subprocess.check_output(
                ["task", "list", "project:{}".format(project_name)],
                stderr=subprocess.STDOUT)
            task_list = task_list.decode('utf-8')
            task_list = f'```\n{task_list}\n```'
            await interaction.followup.send(
                f'Задачи в проекте {project_name}: \n{task_list}')
        except subprocess.CalledProcessError:
            await interaction.followup.send(
                'Нет задач в этом проекте.')

# Фильтр по тегу


class FilterByTagButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Фильтр по тегу',
                         row=1,
                         custom_id='filter_by_tag',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Введите интересующие теги, разделенные пробелами")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        tags = message.content.strip().split()

        task_list = ''
        for tag in tags:
            try:
                current_task_list = subprocess.check_output(
                    ["task", "list", "+{}".format(tag)],
                    stderr=subprocess.STDOUT)
                current_task_list = current_task_list.decode('utf-8')
                task_list += f'Задачи с тегом {tag}: \n```\n{current_task_list}\n```\n'
            except subprocess.CalledProcessError:
                task_list += f'Нет задач с тегом {tag}.\n'

        await interaction.followup.send(task_list)

# Удаление тега из задачи


class RemoveTagFromTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Удалить тег из задачи',
                         row=0,
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи и тег (через пробел)")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        task_id, tag = message.content.split()
        subprocess.run(["task", task_id, "modify", "-"+tag])
        await interaction.followup.send(f'Тег {tag} удален из задачи {task_id}.')

 # Просмотр всех тегов в задаче


class ViewTagsInTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Просмотреть теги в задаче',
                         row=1,
                         style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        task_id = message.content.strip()

        try:
            task_info = subprocess.check_output(["task", task_id, "info"], stderr=subprocess.STDOUT)
            task_info = task_info.decode('utf-8')
            # Извлечение тегов из информации о задаче
            tags_line = next((line for line in task_info.split('\n') if line.startswith('Tags')), None)
            if tags_line is not None:
                tags = ', '.join(tags_line.split()[1:])
                await interaction.followup.send(f'Теги в задаче {task_id}: {tags}')
            else:
                await interaction.followup.send(f'В задаче {task_id} нет тегов.')
        except subprocess.CalledProcessError:
            await interaction.followup.send('Не удалось получить информацию о задаче.')

# Просмотр всех тегов


class ViewAllTagsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Все теги проекта',
                         row=1,
                         style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        try:
            task_list = subprocess.check_output(["task", "export"], stderr=subprocess.STDOUT)
            tasks = json.loads(task_list)

            # Извлечение тегов из каждой задачи
            tags = set()
            for task in tasks:
                if 'tags' in task:
                    tags.update(task['tags'])

            if tags:
                await interaction.response.send_message(f'Все теги: {", ".join(tags)}')
            else:
                await interaction.response.send_message('На удивление, тут ещё нет тегов.')
        except subprocess.CalledProcessError:
            await interaction.response.send_message('Произошла какая-то ошибка при получении списка тегов.')

# Переименовывание тега


class RenameTagButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Сменить тег задачи',
                         row=0,
                         custom_id='rename_tag',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите старое и новое имя тега (через пробел)")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        old_tag, new_tag = message.content.split()
        subprocess.run(["task", "tag:{0}".format(old_tag), "modify", "+"+new_tag, "-"+old_tag])
        await interaction.followup.send(
            f'Тег {old_tag} переименован в {new_tag}.')
        
# Удаление тега из всех задач:


class DeleteTagButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Удалить тег',
                         row=0,
                         custom_id='delete_tag',
                         style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите имя тега для удаления")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        tag = message.content
        subprocess.run(["task", "tag:{0}".format(tag), "modify", "-"+tag])
        await interaction.followup.send(
            f'Тег {tag} удален из всех задач.')

# Изменение приоритета задачи


class ChangePriorityButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Назначить приоритет",
                         row=0,
                         style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = PriorityView()
        await interaction.response.send_message("Выберите приоритет:", view=view)

class PriorityButton(discord.ui.Button):
    def __init__(self, label, priority):
        super().__init__(label=label,
                         row=0,
                         custom_id=f'priority_{priority}',
                         style=discord.ButtonStyle.primary)
        self.task_id = None
        self.priority = priority

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        self.task_id = message.content

        subprocess.run(["task", self.task_id, "modify", f"priority:{self.priority}"])
        await interaction.followup.send(
            f'Приоритет задачи {self.task_id} изменен на {self.priority}.')
        
class PriorityView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PriorityButton("Низкий", "L"))
        self.add_item(PriorityButton("Средний", "M"))
        self.add_item(PriorityButton("Высокий", "H"))

# Установка даты завершения задачи
class ChangeDueDateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Назначить дату завершения",
                         row=0,
                         style=discord.ButtonStyle.primary)
        self.task_id = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи")

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )
        message = await bot.wait_for('message', check=check)
        self.task_id = message.content

        await interaction.followup.send("Введите новую дату завершения (в формате YYYY-MM-DD)")

        message = await bot.wait_for('message', check=check)
        new_due_date = message.content

        subprocess.run(["task", self.task_id, "modify", f"due:{new_due_date}"])
        await interaction.followup.send(f'Дата завершения задачи {self.task_id} изменена на {new_due_date}.')

# Кнопка назад

class BackButton1(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Назад',
                         row=2,
                         custom_id='back_button1',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=MainView())

class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Назад',
                         row=3,
                         custom_id='back_button',
                         style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=MainView())

# Представление кнопок


class WorkingView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(MyTasksButton())
        self.add_item(DoneTaskButton())
        self.add_item(BackButton1())

class BasicView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CreateTaskButton())
        self.add_item(DeleteTasksButton())
        self.add_item(ChangePriorityButton())
        self.add_item(ChangeDueDateButton())
        self.add_item(AddProjectButton())
        self.add_item(ListTasksButton())
        self.add_item(CompletedTasksButton())
        self.add_item(FilterByProjectButton())
        self.add_item(FilterByTagButton())
        self.add_item(BackButton())

class TagManagementView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(AddTagButton())
        self.add_item(RemoveTagFromTaskButton())
        self.add_item(ViewAllTagsButton())
        self.add_item(ViewTagsInTaskButton())
        self.add_item(RenameTagButton())
        self.add_item(DeleteTagButton())
        self.add_item(BackButton())
        
bot.run(TOKEN)