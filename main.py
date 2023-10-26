import discord
import subprocess
from discord.ui import Button, View
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
PREFIX = os.getenv('PREFIX')
ALLOWED_CHANNEL_ID = os.getenv('ALLOWED_CHANNEL_ID')

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"We a started! We got colors!")

class MainView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Manage', style=discord.ButtonStyle.green)
    async def menu_button(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.edit_message(content="Выберите действие", view=ManageView())

#СОЗДАТЬ ЗАДАЧУ
class CreateTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Создать задачу', row=0, custom_id='create_task', style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите название для задачи")
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        message = await bot.wait_for('message', check=check)
        task_description = message.content

        await interaction.followup.send('Хотите ли вы назначить эту задачу определенному пользователю? (y/n)')
        message = await bot.wait_for('message', check=check)
        if message.content.lower() == 'y':
            await interaction.followup.send('Введите имя пользователя.')
            message = await bot.wait_for('message', check=check)
            user_name = message.content
            # Проверка, существует ли пользователь с этим именем на сервере
            user = interaction.guild.get_member_named(user_name)
            if user is None:
                await interaction.followup.send(f'Пользователь {user_name} не найден.')
                return
            # Замена всех спец. символов и пробелов на подчеркивания
            user_tag = ''.join(e if e.isalnum() else '_' for e in user_name)
            subprocess.run(["task", "add", task_description, f"+{user_tag}"])
            await interaction.followup.send(f'Задача "{task_description}" создана и назначена пользователю {user_name}.')
        else:
            subprocess.run(["task", "add", task_description])
            await interaction.followup.send(f'Задача "{task_description}" создана.')

#Добавить проект
class AddProjectButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Добавить проект', row=0, custom_id='add_project', style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи и название проекта (через пробел)")
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        message = await bot.wait_for('message', check=check)
        task_id, project_name = message.content.split()
        subprocess.run(["task", task_id, "modify", "project:"+project_name])
        await interaction.followup.send(f'Задача {task_id} отправлена в проект {project_name}.')

#Добавить тэг
class AddTagButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Добавить тэг', row=0, custom_id='add_tag', style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи и тэг (через пробел)")
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        message = await bot.wait_for('message', check=check)
        task_id, tag = message.content.split()
        subprocess.run(["task", task_id, "modify", "+"+tag])
        await interaction.followup.send(f'Тэг {tag} добавлен в задачу {task_id}.')

#МОИ ЗАДАЧИ
class MyTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Мои задачи', row=1, custom_id='my_tasks', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name
        # Замена всех спец. символов и пробелов на подчеркивания
        user_tag = ''.join(e if e.isalnum() else '_' for e in user_name)
        # Получение задачи с тегом, соответствующим user_tag
        tag_argument = "+{0}".format(user_tag)
        try:
            task_list = subprocess.check_output(["task", tag_argument, "list"], stderr=subprocess.STDOUT)
            task_list = task_list.decode('utf-8')
            task_list = f'```\n{task_list}\n```'
            await interaction.response.send_message(f'Ваши задачи: {task_list}')
        except subprocess.CalledProcessError:
            await interaction.response.send_message(f'У вас нет задач.')

#ВСЕ ЗАДАЧИ
class ListTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Список всех задач', row=2, custom_id='list_tasks', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        # Проверка на админа
        if interaction.user.guild_permissions.administrator:
            try:
                task_list = subprocess.check_output(["task", "list"], stderr=subprocess.STDOUT)
                task_list = task_list.decode('utf-8')
                task_list = f'```\n{task_list}\n```'
                await interaction.response.send_message(f'Здесь все задачи: {task_list}')
            except subprocess.CalledProcessError:
                await interaction.response.send_message('Список задач пуст.')
        else:
            await interaction.response.send_message('У вас нет доступа к этой функции.')

#УДАЛЕНИЕ ЗАДАЧ
class DeleteTasksButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Удаление задач', row=3, custom_id='delete_task', style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Введите ID задачи для удаления")
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        message = await bot.wait_for('message', check=check)
        task_id = message.content
        await interaction.followup.send(f'Вы уверены, что хотите удалить задачу {task_id}? (y/n)')
        message = await bot.wait_for('message', check=check)
        if message.content.lower() == 'y':
            task_ids = task_id.split()
            for task in task_ids:
                subprocess.run(["task", "rc.confirmation=no", task, "delete"])
            await interaction.followup.send(f'Задачи {task_id} удалены.')
        else:
            await interaction.followup.send(f'Удаление задачи {task_id} отменено.')

class ManageView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CreateTaskButton())
        self.add_item(AddProjectButton())
        self.add_item(AddTagButton())
        self.add_item(MyTasksButton())
        self.add_item(ListTasksButton())
        self.add_item(DeleteTasksButton())
        
#Создать таску
#    async def create_task_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        await interaction.response.send_message("Введите название для задачи")
#        def check(m):
#            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
#        message = await bot.wait_for('message', check=check)
#        task_description = message.content
#
#        await interaction.followup.send('Хотите ли вы назначить эту задачу определенному пользователю? (y/n)')
#        message = await bot.wait_for('message', check=check)
#        if message.content.lower() == 'y':
#            await interaction.followup.send('Введите имя пользователя.')
#            message = await bot.wait_for('message', check=check)
#            user_name = message.content
#            # Проверка, существует ли пользователь с этим именем на сервере
#            user = interaction.guild.get_member_named(user_name)
#            if user is None:
#                await interaction.followup.send(f'Пользователь {user_name} не найден.')
#                return
#            # Замена всех спец. символов и пробелов на подчеркивания
#            user_tag = ''.join(e if e.isalnum() else '_' for e in user_name)
#            subprocess.run(["task", "add", task_description, f"+{user_tag}"])
#            await interaction.followup.send(f'Задача "{task_description}" создана и назначена пользователю {user_name}.')
#        else:
#            subprocess.run(["task", "add", task_description])
#            await interaction.followup.send(f'Задача "{task_description}" создана.')

#Список всех задач
#    async def list_tasks_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        task_list = subprocess.check_output(["task", "list"])
#        task_list = task_list.decode('utf-8')
#        task_list = f'```\n{task_list}\n```'
#        await interaction.response.send_message(f'Здесь все задачи: {task_list}')

#Добавить проект
#    @discord.ui.button(label='Добавить проект', style=discord.ButtonStyle.green)
#    async def project_tasks_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        await interaction.response.send_message("Введите ID задачи и название проекта (через пробел)")
#        def check(m):
#            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
#        message = await bot.wait_for('message', check=check)
#        task_id, project_name = message.content.split()
#        subprocess.run(["task", task_id, "modify", "project:"+project_name])
#        await interaction.followup.send(f'Задача {task_id} отправлена в проект {project_name}.')

#Мои задачи
#    async def my_tasks_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        user_name = interaction.user.name
#        # замените все специальные символы и пробелы на подчеркивания
#        user_tag = ''.join(e if e.isalnum() else '_' for e in user_name)
#        # Получите задачи с тегом, соответствующим user_tag
#        tag_argument = "+{0}".format(user_tag)
#        try:
#            task_list = subprocess.check_output(["task", tag_argument, "list"], stderr=subprocess.STDOUT)
#            task_list = task_list.decode('utf-8')
#            task_list = f'```\n{task_list}\n```'
#            await interaction.response.send_message(f'Ваши задачи: {task_list}')
#        except subprocess.CalledProcessError:
#            await interaction.response.send_message(f'У вас нет задач.')

#Добавить тег
#    @discord.ui.button(label='Добавить тэг', style=discord.ButtonStyle.green)
#    async def tag_tasks_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        await interaction.response.send_message("Введите ID задачи и тэг (через пробел)")
#        def check(m):
#            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
#        message = await bot.wait_for('message', check=check)
#        task_id, tag = message.content.split()
#        subprocess.run(["task", task_id, "modify", "+"+tag])
#        await interaction.followup.send(f'Тэг {tag} добавлен в задачу {task_id}.')

#Удаление задач
#    async def delete_tasks_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        await interaction.response.send_message("Введите ID задачи для удаления")
#        def check(m):
#            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
#        message = await bot.wait_for('message', check=check)
#        task_id = message.content
#        await interaction.followup.send(f'Вы уверены, что хотите удалить задачу {task_id}? (y/n)')
#        message = await bot.wait_for('message', check=check)
#        if message.content.lower() == 'y':
#            task_ids = task_id.split()
#            for task in task_ids:
#                subprocess.run(["task", "rc.confirmation=no", task, "delete"])
#            await interaction.followup.send(f'Задачи {task_id} удалены.')
#        else:
#            await interaction.followup.send(f'Удаление задачи {task_id} отменено.')

#Задачи по тегу
#    @discord.ui.button(label='Задачи по тегу', style=discord.ButtonStyle.green)
#    async def tag_projects_button(self, interaction: discord.Interaction, button: discord.ui.button):
#        await interaction.response.send_message("Введите тэг для просмотра списка задач")
#        def check(m):
#            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
#        message = await bot.wait_for('message', check=check)
#        tag = message.content
#        task_list = subprocess.check_output(["task", "list", "+" + tag])
#        task_list = task_list.decode('utf-8')
#        task_list = f'```\n{task_list}\n```'
#        await interaction.followup.send(f'Здесь все ваши задачи с тэгом {tag}: {task_list}')

@bot.command()
async def hello(ctx):
    await ctx.send("Приветствую", view=MainView())
    

@bot.command(name='test') 
async def test(ctx): await ctx.send('Test successful!')

#@bot.command(name='create')
#async def create_task(ctx, *args):
#    # Joining the args by space to form the task description
#    task_description = " ".join(args[:])
#    subprocess.run(["task", "add", task_description])
#    await ctx.send(f'Task "{task_description}" created.')

#@bot.command(name='list')
#async def list_tasks(ctx):
#    # Using subprocess to get the output of 'task list'
#    task_list = subprocess.check_output(["task", "list"])
#    task_list = task_list.decode('utf-8')
#    task_list = f'```\n{task_list}\n```'
#    await ctx.send(f'Here are your tasks: {task_list}')

#@bot.command(name='set_project')
#async def set_project(ctx, task_id, project_name):
#    subprocess.run(["task", task_id, "modify", "project:"+project_name])
#    await ctx.send(f'Task {task_id} moved to project {project_name}.')

#@bot.command(name='add_tag')
#async def add_tag(ctx, task_id, tag):
#    subprocess.run(["task", task_id, "modify", "+"+tag])
#    await ctx.send(f'Tag {tag} added to task {task_id}.')


@bot.command()
async def task(ctx, *, task_command):
    """Execute a taskd command"""
    
    # Check if the command is from the allowed channel
    if ctx.guild and ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send("Sorry, you can't use this command here.")
        return

    try:
        process = subprocess.Popen(["task", *task_command.split()], 
                                   stdin=subprocess.PIPE, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
        
        # Send 'yes' to stdin and collect the output
        stdout, stderr = process.communicate(input="yes\n")

        result = stdout or stderr

        # Split the result into multiple messages if it's too long
        for chunk in [result[i:i + 1900] for i in range(0, len(result), 1900)]:
            await ctx.send(f"```\n{chunk}\n```")
    except Exception as e:
        await ctx.send(f"Error executing task: {e}")

bot.run('TOKEN')