## IMPORTS

import sqlite3
#from venv import create
import requests
import json
import math
import shutil
import os

from bot_token import bot_token
from discord.ext import commands





## INTIALIZE

connection = sqlite3.connect('tweets.db')
cursor = connection.cursor()

client = commands.Bot(command_prefix='wh')





## FUNCTION DEFS

def get_table(table, sort_by = None):
    # takes the name of a table and returns all data within the table

    command = f'SELECT * FROM {table}'
    if type(sort_by) == str:
        command += f' ORDER BY {sort_by} Asc'
    command += ";"

    cursor.execute(command)
    return cursor.fetchall()

def list_to_text(list, code = False):
    # takes a list and converts to text form
    # code == True: backticks around each element

    output = ""

    if len(list) > 0:
        i = 0

        while i < (len(list) - 1):
            element = list[i]
            if code:
                element = "`" + element + "`"

            output += f'{element}, '
            i += 1

        element = list[i]
        if code:
            element = "`" + element + "`"
        output += element

    return output

def save_file(file_to_save, location):
    file = open(location, "w")
    file.write(file_to_save)
    file.close()


def new_tag(tag_name):
    cursor.execute(f'INSERT INTO Tags (tag) VALUES (\'{tag_name}\');')

def get_tag(tag_ref):
    # takes the id or name of a tag and returns both in a list

    tag_ref = str(tag_ref)

    if tag_ref[:1] == "#":
        #tag name
        cursor.execute(f'SELECT * FROM Tags WHERE tag = \'{tag_ref}\';')
    else:
        #tag id
        cursor.execute(f'SELECT * FROM Tags WHERE id = {tag_ref};')
    
    tag_data = list(cursor.fetchall()[0])
    return tag_data

def tags_from_tweet_id(tweet_db_id):
    # takes the db id of a tweet and returns the ids of all tags assigned to that tweet
    cursor.execute(f'SELECT * FROM TagAssigns WHERE tweet_db_id = {tweet_db_id} ORDER BY tweet_db_id Desc;')

    assign_data = list(cursor.fetchall())
    tag_ids = []

    for i in assign_data:
        tag_ids.append(i[2])

    return tag_ids

def tweets_from_tag_id(tag_db_id):
    # takes the db id of a tag and returns the ids of all tweets with the tag
    # tag id -1 returns all tweets, tag id 0 returns tweets with no tags

    tweet_db_ids = []

    if tag_db_id == -1:
        tweet_data = get_table("Tweets")
        for i in tweet_data:
            tweet_db_ids.append(i[0])

    elif tag_db_id == 0:
        tweet_data = tweets_with_no_tags()
        for i in tweet_data:
            tweet_db_ids.append(i[0])
        
    else:
        cursor.execute(f'SELECT * FROM TagAssigns WHERE tag_db_id = {tag_db_id} ORDER BY tweet_db_id Asc;')
        assign_data = list(cursor.fetchall())
        for i in assign_data:
            tweet_db_ids.append(i[1])

    return tweet_db_ids

def assign_tags(tweet_db_id, tag_refs):
    # takes a tweet database id and a list of tag refs (id or name) and assigns all tweets to the tag
    # returns the name of all assigned and created tags

    assigned_tags = []
    new_tags = []

    for tag_ref in tag_refs:
        try:
            tag_data = get_tag(tag_ref)
        except:
            # if tag does not exist
            if tag_ref[:1] == "#":
                new_tag(tag_ref)
                new_tags.append(tag_ref)

                tag_data = get_tag(tag_ref)
                assign_tag(tweet_db_id, tag_data[0])
        else:
            assign_tag(tweet_db_id, tag_data[0])
            assigned_tags.append(tag_data[1])
    
    return [assigned_tags, new_tags]

def assign_tag(tweet_id, tag_id):
    #takes an id of tweet and tag and assigns the tag to the tweet

    cursor.execute(f'INSERT INTO TagAssigns (tweet_db_id, tag_db_id) VALUES (\'{tweet_id}\', \'{tag_id}\');')


def generate_response(type, info=[], additions=[], additions_info=[]):
    # generates a response according to given info, response type, and additions and responds using given context

    response = ""

    if type == "a":
        # add tweet
        # info: [0] username, [1] tweet_id
        response += f'Tweet from `{info[0]}` added with id `{info[1]}`!'
    elif type == "nt":
        # new tag
        # info: [0] tag names
        response += f'Tag{"s" if len(info[0]) > 1 else ""} {info[0]} added!'
    elif type == "at":
        # assign tag
        # info: [0] assigned tags, [1] created tags, [2] tweet link
        response += f'Tag{"s" if (len(info[0]) + len(info[1])) > 1 else ""} assigned to <{info[2]}>'
    elif type == "b":
        # build page
        # info: none
        response += f'Pages built successfully!'
    elif type == "rtw":
        # read tweets
        # info: none
        response += "```"
        for i in get_table("Tweets"):
            response += f'{i[0]}. {tweet_link(i[1], i[2])}\n'

            tag_names = []
            for tag_id in tags_from_tweet_id(i[0]):
                tag_names.append(get_tag(tag_id)[1])
            if len(tag_names) > 0:
                response += f'{list_to_text(tag_names)}\n'
            
            response += "\n"

        response += "```"
    elif type == "rta":
        # read tags
        # info: none
        response += "```"
        for i in get_table("Tags"):
            response += f'{i[0]}. {i[1]}\n'
        response += "```"
    elif type == "ras":
        # read assigns
        # info: none
        response += "```"
        for i in get_table("TagAssigns"):
            response += f'{i[0]}. {i[1]} {get_tag(i[2])[1]}\n'
        response += "```"

    for addition in additions:
        response += f'\n'

        if addition == "at":
            # assigned tags
            # info: [0] assigned tags, [1] created tags
            response += f'Tags Assigned: {additions_info[0]}\nTags Created: {additions_info[1]}'
    
    return response


def tweet_link(id, username):
    return f'https://twitter.com/{username}/status/{id}'

def find_tweet(tweet_db_id):
    # takes the db id of a tweet and returns db id, username, tweet_id, and link

    cursor.execute(f'SELECT * FROM Tweets WHERE id = {tweet_db_id};')
    tweet_data = list(cursor.fetchall()[0])
    tweet_data.append(tweet_link(tweet_data[1], tweet_data[2]))
    return tweet_data

def find_tweet_db_id(tweet_id):
    # takes the id of a tweet and returns db id, username, tweet_id, and link

    cursor.execute(f'SELECT * FROM Tweets WHERE tweet_id = {tweet_id};')
    tweet_data = list(cursor.fetchall()[0])
    tweet_data.append(tweet_link(tweet_data[1], tweet_data[2]))
    return tweet_data

def tweets_with_no_tags():
    # returns the info of all tweets that have no tags

    tweets_list = get_table("Tweets")
    assigns_list = get_table("TagAssigns")
    tweet_ids_with_tags = []
    tweets_with_no_tags = []

    for assignment in assigns_list:
        tweet_ids_with_tags.append(assignment[1])
    
    for tweet_info in tweets_list:
        if tweet_info[0] not in tweet_ids_with_tags:
            tweets_with_no_tags.append(tweet_info)

    return tweets_with_no_tags


def build_pages(template_file, max_tweets):
    page_split = template_file.split(f'<div id="dummy"></div>')
    return_dirs = []
    return_files = []
    tags_list = [(-1, "#all"), (0, "#none")] + (get_table("Tags", "tag"))
    tag_links = make_tag_links(tags_list)

    for tag_info in tags_list:
        tag_name = tag_info[1]
        return_dirs.append(tag_name[1:])
        tweet_db_ids = tweets_from_tag_id(tag_info[0])
        pages = math.ceil(len(tweet_db_ids) / max_tweets)
        page_links = make_page_links(tag_name, pages)

        tweet_previews = ""
        page_num = 1
        i = 0

        for tweet_db_id in reversed(tweet_db_ids):
            tweet_previews += make_tweet_preview(find_tweet(tweet_db_id))
            i += 1
            
            if i >= max_tweets:
                new_page = page_split[0] + make_page_title(f'Saved Tweets', f'{tag_name} - {page_num}') + tag_links + page_links + tweet_previews + make_page_title(None, f'{tag_name} - {page_num}') + page_links + page_split[1]
                return_files.append([f'{tag_name[1:]}/{page_num}', new_page])

                tweet_previews = ""
                page_num += 1
                i = 0
        
        new_page = page_split[0] + make_page_title(f'Saved Tweets', f'{tag_name} - {page_num}') + tag_links + page_links + tweet_previews + make_page_title(None, f'{tag_name} - {page_num}') + page_links + page_split[1]
        return_files.append([f'{tag_name[1:]}/{page_num}', new_page])

    return [return_dirs, return_files]

def make_page_title(title = None, subtitle = None):
    elements = ""
    if type(title) == str:
        elements += f'<h1 style="text-align:center;">{title}</h1>\n'
    if type(subtitle) == str:
        elements += f'<h2 style="text-align:center;">{subtitle}</h2>\n'
    elements += "\n"

    return elements

def make_tweet_preview(tweet_info):
    #tweet_info: [0]tweet_db_id, [1]tweet_id, [2]username

    preview = f'<div align="center">'
    preview += f'<h2>{tweet_info[0]}. </h2>'
    preview += make_tweet_tag_info(tweet_info[0])
    preview += tweet_embed(tweet_info)
    preview += f'</div>\n\n'

    return preview

def make_tweet_tag_info(tweet_id):
    response = f'<p>'

    tag_names = []
    for tag_info in tags_from_tweet_id(tweet_id):
        try:
            tag_names.append(get_tag(tag_info)[1])
        except:
            print(f'tag {tag_info} not found')
    if len(tag_names) > 0:
        response += f'{list_to_text(tag_names)}'

    response += "</p>"
    return response

def tweet_embed(tweet_info):
    #tweet_info: [0]tweet_db_id, [1]tweet_id, [2]username
    cursor.execute(f'SELECT * FROM TweetEmbeds WHERE id = {tweet_info[0]};')
    embed_data = list(cursor.fetchall())

    if len(embed_data) == 0:
        embed = fetch_tweet_embed(tweet_link(tweet_info[1], tweet_info[2])) 
        cursor.execute(f'INSERT INTO TweetEmbeds (id, embed) VALUES ({tweet_info[0]}, \'{embed}\');')
        connection.commit()
    else:
        embed = embed_data[0][1]
    
    return embed

def fetch_tweet_embed(url):
    # takes a tweet url and returns the corresponding html embed for the tweet
    resp = requests.get(f'https://publish.twitter.com/oembed?theme=dark&omit_script=t&url={url}')

    try:
        json_data = json.loads(bytes.decode(resp.content))
    except:
        return f'<p>Tweet does not exist.</p>'
    else:
        try:
            return_data = json_data["html"]
        except:
            return f'<p>{json_data["error"]}</p>'
        else:
            return return_data


def make_tag_links(tags_list):
    return_data = f'<div align="center">'
    for tag_info in tags_list:
        return_data += f'<a href="../{tag_info[1][1:]}/1.html">{tag_info[1]}</a>&ensp;'
    return_data += f'</div>\n\n'

    return return_data

def make_page_links(tag_name, pages):
    return_data = f'<div align="center">'
    for i in range(1, pages + 1):
        return_data += f'<a href="../{tag_name[1:]}/{i}.html">{i}</a>&emsp;&emsp;'
    return_data += f'</div>\n\n'

    return return_data






## BOT STUFF

@client.event
async def on_ready():
    print('Ready!')


@client.command(aliases=['a', 'add'])
async def addtweet(ctx, *, input=""):
    try:
        args = input.split(" ")
        url = args[0].split("?")[0]
        url_split = url.split("/")
        
        username = url_split[3]
        tweet_id = url_split[5]

        cursor.execute(f'INSERT INTO Tweets (tweet_id, username) VALUES ({tweet_id}, \'{username}\');')
        
        if len(args) > 1:
            try:
                tweet_db_id = find_tweet_db_id(tweet_id)[0]
                tag_refs = args[1:]
                returned_data = assign_tags(tweet_db_id, tag_refs)

                assigned_tags = list_to_text(returned_data[0], True)
                created_tags = list_to_text(returned_data[1], True)
            except Exception as ex:
                await ctx.send(f'Error while trying to assign tag(s): \n{ex}')

        await buildpages(ctx, True)
    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to add <{url}> to DB:\n{ex}')
        connection.rollback()
    else:
        if len(args) > 1:
            await ctx.reply(generate_response("a", [username, tweet_id], ["at"], [assigned_tags, created_tags]))
        else:
            await ctx.reply(generate_response("a", [username, tweet_id]))
        
        connection.commit()

@client.command(aliases=['d', 'del', 'delete', 'deltweet'])
async def deletetweet(ctx, *, input=""):
    try:
        db_ids = input.split(" ")
        deleted_tweets = []

        for db_id in db_ids:
            cursor.execute(f'SELECT * FROM Tweets WHERE id = {db_id}')
            deleted_tweets.append(list(cursor.fetchall()[0]))

            cursor.execute(f'DELETE FROM Tweets WHERE id = {db_id}')
            cursor.execute(f'DELETE FROM TagAssigns WHERE tweet_db_id = {db_id}')
            cursor.execute(f'DELETE FROM TweetEmbeds WHERE id = {db_id}')
        
        await buildpages(ctx, True)

    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to remove tweets <{db_ids}> from DB:\n{ex}')
        connection.rollback()
    else:
        tweet_links = []

        for tweet_info in deleted_tweets:
            tweet_links.append(f'<{tweet_link(tweet_info[1], tweet_info[2])}>')

        await ctx.reply(f'Successfully deleted tweet{"s" if len(deleted_tweets) > 1 else ""}:\n{list_to_text(tweet_links)}')

        connection.commit()

@client.command(aliases=['rep', 'replace', 'reptweet'])
async def replacetweet(ctx, *, input=""):
    try:
        args = input.split(" ")
        tweet_delete = args[0]
        tweet_delete_link = find_tweet(tweet_delete)[3]
        tweet_add = args[1]

        cursor.execute(f'DELETE FROM Tweets WHERE id = {tweet_delete}')

        url = tweet_add.split("?")[0]
        url_split = url.split("/")
        
        username = url_split[3]
        tweet_id = url_split[5]

        cursor.execute(f'INSERT INTO Tweets (tweet_id, username) VALUES ({tweet_id}, \'{username}\');')

        await buildpages(ctx, True)

    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to replace tweets:\n{ex}')
        connection.rollback()
    else:
        await ctx.reply(f'Successfully replaced <{tweet_delete_link}> with <{tweet_link(tweet_id, username)}>!')

        connection.commit()

@client.command(aliases=['i', 'insert'])
async def inserttweet(ctx, *, input=""):
    try:
        args = input.split(" ")
        db_id = args[0]
        tweet_add = args[1]

        url = tweet_add.split("?")[0]
        url_split = url.split("/")
        
        username = url_split[3]
        tweet_id = url_split[5]

        cursor.execute(f'INSERT INTO Tweets (id, tweet_id, username) VALUES ({db_id}, {tweet_id}, \'{username}\');')
        
        await buildpages(ctx, True)

    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to insert tweet:\n{ex}')
        connection.rollback()
    else:
        await ctx.reply(f'Tweet from `{username}` inserted with id `{tweet_id}` at database id `{db_id}`!')

        connection.commit()


@client.command(aliases=['nt', 'addtag'])
async def newtag(ctx, *, input):
    try:
        tag_names = input.split(" ")

        for tag_name in tag_names:
            new_tag(tag_name)
        
        await buildpages(ctx, True)
    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to add tag{"s" if len(tag_names) > 1 else ""} {tag_names} to DB:\n{ex}')

        connection.rollback()
    else:
        await ctx.reply(generate_response("nt", [tag_names]))

        connection.commit()

@client.command(aliases=['dt', 'deltag'])
async def deletetag(ctx, *, input=""):
    try:
        tag_refs = input.split(" ")
        deleted_tags = []

        for tag_ref in tag_refs:
            tag_info = get_tag(tag_ref)
            cursor.execute(f'SELECT * FROM Tags WHERE id = {tag_info[0]}')
            deleted_tags.append(list(cursor.fetchall()[0]))

            cursor.execute(f'DELETE FROM Tags WHERE id = {tag_info[0]}')
            cursor.execute(f'DELETE FROM TagAssigns WHERE tag_db_id = {tag_info[0]}')
        
        await buildpages(ctx, True)

    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to remove tags:\n{ex}')
        connection.rollback()

    else:
        tag_names = []

        for tag_info in deleted_tags:
            tag_names.append(tag_info[1])

        await ctx.reply(f'Successfully deleted tag{"s" if len(deleted_tags) > 1 else ""}!\nDeleted Tags: {list_to_text(tag_names, True)}')

        connection.commit()

@client.command(aliases=['at', 'tag'])
async def assigntag(ctx, *, input=""):
    try:
        args = input.split(" ")

        tweet_db_id = args[0]
        args.pop(0)
        tag_refs = args

        returned_data = assign_tags(tweet_db_id, tag_refs)

        await buildpages(ctx, True)

    except Exception as ex:
        await ctx.send(f'Error while trying to assign tag(s): \n{ex}')
        connection.rollback()
    else:
        tweet_link = find_tweet(tweet_db_id)[3]

        assigned_tags = list_to_text(returned_data[0], True)
        created_tags = list_to_text(returned_data[1], True)

        await ctx.reply(generate_response("at", [assigned_tags, created_tags, tweet_link], ["at"], [assigned_tags, created_tags]))
        connection.commit()

@client.command(aliases=['ut', 'untag'])
async def unassigntag(ctx, *, input=""):
    try:
        args = input.split(" ")

        tweet_db_id = args[0]
        tag_ref = args[1]
        tag_db_id = get_tag(tag_ref)[0]

        cursor.execute(f'DELETE FROM TagAssigns WHERE tweet_db_id = {tweet_db_id} AND tag_db_id = {tag_db_id}')

        await buildpages(ctx, True)
        
    except Exception as ex:
        await ctx.send(f'Error while trying to remove tag: \n{ex}')
        connection.rollback()
    else:
        await ctx.reply(f'Successfully unassigned tag `{get_tag(tag_ref)[1]}` from tweet <{find_tweet(tweet_db_id)[3]}>!')
        connection.commit()



@client.command(aliases=['r', 'read'])
async def readdb(ctx, input="tweets"):
    if input.startswith("tw"):
        # tweets
        response_type = "rtw"
    elif input.startswith("ta"):
        # tags
        response_type = "rta"
    elif input.startswith("a"):
        # assigns
        response_type = "ras"
    
    await ctx.reply(generate_response(response_type))

@client.command(aliases=['b', 'build'])
async def buildpages(ctx, quiet=False):
    if not quiet:
        await ctx.send(f'Building pages please wait...')

    try:
        shutil.rmtree("html/saved-tweets", ignore_errors = True)
        os.mkdir("html/saved-tweets")

        template_file = open('saved-tweets-template.html', 'r')
        template_page = template_file.read()
        template_file.close()

        function_data = build_pages(template_page, 15)
        directory_names = function_data[0]
        built_tweet_pages = function_data[1]

        for dir_name in directory_names:
            os.mkdir(f'html/saved-tweets/{dir_name}')

        for page in built_tweet_pages:
            save_file(page[1], f'html/saved-tweets/{page[0]}.html')

    except Exception as ex:
        await ctx.channel.purge(limit = 1)
        await ctx.send(f'Error while trying to build pages: {ex}')
        connection.rollback()

    else:
        if not quiet:
            await ctx.channel.purge(limit = 1)
            await ctx.reply(generate_response("b"))
            
        connection.commit()

@client.command()
async def stop(ctx):
    connection.commit()
    connection.close()

    await ctx.channel.purge(limit = 1)

    await client.close()

@client.command(aliases=['t'])
async def test(ctx, *, input=""):
    print("hi")


# RUN LOOP
client.run(bot_token)