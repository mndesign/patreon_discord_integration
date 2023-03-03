import discord
import os
import json
import patreon
import datetime
from dotenv import load_dotenv
from startup import Startup
from discord.ext import commands

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix='.', 
    intents=intents, 
    application_id=os.getenv("APP_ID"))

os.system('cls' if os.name == 'nt' else 'clear')

@bot.event
async def on_ready():
    Startup(bot.user.name)

@bot.event
async def on_message( message ):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PatreonRole = []
    api_client = patreon.API(os.getenv("PATREON_TOKEN"))

    #Get campaign ID
    campaign_response = api_client.fetch_campaign()
    campaign_id = campaign_response.data()[0].id()

    #Get active roles on Patreon
    for rewardRole in campaign_response.data()[0].relationship('rewards'):
        if rewardRole.attribute('title') != None:
            PatreonRole.append(rewardRole.attribute('title'))

    all_pledges = []
    cursor = None
    while True:
        pledges_response = api_client.fetch_page_of_pledges(
            campaign_id, 
            25, 
            cursor=cursor,
            fields = {'pledge': ['total_historical_amount_cents', 'declined_since']}
        )

        cursor = api_client.extract_cursor(pledges_response)
        all_pledges += pledges_response.data()
        if not cursor:
            break

    pledges_info = []
    
    for pledge in all_pledges:
        declined = pledge.attribute('declined_since')
        reward_tier = 0

        #Check if they have any tiers
        if pledge.relationships()['reward']['data']:
            reward_tier = pledge.relationship('reward').attribute('amount_cents')

        pledges_info.append({
            'full_name': pledge.relationship('patron').attribute('full_name'),
            'total_historical_amount_cents': pledge.attribute('total_historical_amount_cents'),
            'patron_status': pledge.relationship('reward').attribute('status'),
            'tier': pledge.relationship('reward').attribute('title'),
            'discord_role': pledge.relationship('reward').attribute('discord_role_ids')[0],
            'discord_id': pledge.relationship('patron').attribute('social_connections')['discord']['user_id']
            })                
            
        for pledge in pledges_info:
            has_role = 0    
            #Give role to user
            member = message.guild.get_member(int(pledge['discord_id']))
            
            if declined or reward_tier < 100:    
                #Check if user has the role
                for singleRole in member.roles:
                    if singleRole.id == int(pledge['discord_role']):
                        role = message.guild.get_role(int(pledge['discord_role']))
                        print(f"{now} - Role {role.name} was removed from {member.name}")
                        await member.remove_roles(role)
            else:
                #Check if user has the role
                for singleRole in member.roles:
                    if singleRole.id == int(pledge['discord_role']):
                        has_role = 1
                
                if has_role == 0:
                    role = message.guild.get_role(int(pledge['discord_role']))
                    print(f"{now} - Role {role.name} was assigned to {member.name}")
                    await member.add_roles(role)

    for singlePatreonRole in PatreonRole:
        role = discord.utils.find(
        lambda r: r.name == singlePatreonRole, message.guild.roles)
        
        for user in message.guild.members:
            if role in user.roles: #all users with that role is found
                foundUser = 0
                if not pledges_info:
                    print(f"{now} - Role {role.name} was removed from {user.name}")
                    await user.remove_roles(role)

                for pledgeID in pledges_info: #get all roles from patreon
                    if int(user.id) == int(pledgeID['discord_id']):
                        if int(role.id) == int(pledgeID['discord_role']):
                            foundUser = 1

                    if foundUser == 0:
                        print(f"{now} - Role {role.name} was removed from {user.name}")
                        await user.remove_roles(role)        
                
bot.run(os.getenv("BOT_TOKEN"))