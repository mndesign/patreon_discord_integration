import discord
import os
import patreon
import datetime
from os import path
from dotenv import load_dotenv
from startup import Startup
from discord.ext import commands
from discord.utils import get

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix='.', 
    intents=intents, 
    application_id=os.getenv("APP_ID"))

os.system('cls' if os.name == 'nt' else 'clear')

#id = uses the roles added to the tier through the Patreon bot
#name = reads the tier name and matches it to the discord role without of using the Patreon bot
readTier = 'name' 

@bot.event
async def on_ready():
    Startup(bot.user.name)

@bot.event
async def on_message( message ):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PatreonRole = []
    api_client = patreon.API(os.getenv("PATREON_TOKEN"))

    campaign_response = api_client.fetch_campaign()
    campaign_id = campaign_response.data()[0].id()

    for rewardRole in campaign_response.data()[0].relationship('rewards'):
        if rewardRole.attribute('title') != None:
            PatreonRole.append(rewardRole.attribute('title'))

    if not path.isfile('tiers.txt'):
        tierFile = open('tiers.txt', 'w')
        for tier in PatreonRole:
            tierFile.write(f"{tier}\n")
        tierFile.close()
    else:
        compList = []
        delList = []

        
        tierFile = open('tiers.txt', 'r')
        for savedTier in tierFile:
            compList.append(savedTier.strip())

        if not compList == PatreonRole:
            newTiers = [item for item in PatreonRole if item not in compList]
            oldTiers = [item for item in compList if item not in PatreonRole]
            
            if newTiers:
                for addTier in newTiers:
                    compList.append(f"{addTier}")
            if oldTiers:
                for delTier in oldTiers:
                    delList.append(delTier)
                    compList.remove(delTier)
            
            with open('tiers.txt', 'w') as newFile:
                for newList in compList: 
                    newFile.write(f"{newList}\n")
                newFile.close()

        #delete tiers not in patreon
        for singleDel in delList:
            role = discord.utils.find(
            lambda r: r.name == singleDel, message.guild.roles)
            
            for user in message.guild.members:
                if role in user.roles:
                    print(f"{now} - Role {role.name} was removed from {user.name}")
                    await user.remove_roles(role)

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

        if pledge.relationships()['reward']['data']:
            reward_tier = pledge.relationship('reward').attribute('amount_cents')
            pledges_info.append({
                'patron_status': pledge.relationship('reward').attribute('status'),
                'tier': pledge.relationship('reward').attribute('title'),
                'discord_role': pledge.relationship('reward').attribute('discord_role_ids'),
                'discord_id': pledge.relationship('patron').attribute('social_connections')['discord']['user_id']
                })                
                
            for pledge in pledges_info:
                member = message.guild.get_member(int(pledge['discord_id']))
                
                if declined or reward_tier < 100:   
                    for singleRole in member.roles:
                        for singlePledgeRole in pledge['discord_role']:
                            if singleRole.id == int(singlePledgeRole):
                                role = message.guild.get_role(int(pledge['discord_role']))
                                print(f"{now} - Role {role.name} was removed from {member.name}")
                                await member.remove_roles(role)
                else:
                    if readTier == 'id':
                        for singlePledgeRole in pledge['discord_role']:
                            role = message.guild.get_role(int(singlePledgeRole))
                            if not role in member.roles:
                                role = message.guild.get_role(int(singlePledgeRole))
                                print(f"{now} - Role {role.name} was assigned to {member.name}")
                                await member.add_roles(role)

                    if readTier == 'name':
                        role = get(message.guild.roles, name=pledge['tier'])
                        if role:
                            if not role in member.roles:
                                print(f"{now} - Role {role.name} was assigned to {member.name}")
                                await member.add_roles(role)
                        else: 
                            print(f"{now} - Missing role '{pledge['tier']}' in Discord Server")


    for singlePatreonRole in PatreonRole:
        role = discord.utils.find(
        lambda r: r.name == singlePatreonRole, message.guild.roles)
        
        for user in message.guild.members:
            foundUser = 0
            if role in user.roles:
                if not pledges_info:
                    print(f"{now} - Role {role.name} was removed from {user.name}")
                    await user.remove_roles(role)

                for pledgeID in pledges_info: 
                    if foundUser != 1: 
                        if int(user.id) == int(pledgeID['discord_id']):
                            if readTier == 'id':
                                for singlePledgeRole in pledgeID['discord_role']:
                                    if int(role.id) == int(singlePledgeRole):
                                        foundUser = 1

                            if readTier == 'name':
                                if role.name == pledgeID['tier']:
                                    foundUser = 1

                if foundUser == 0:
                    print(f"{now} - Role {role.name} was removed from {user.name}")
                    await user.remove_roles(role)        
                
bot.run(os.getenv("BOT_TOKEN"))