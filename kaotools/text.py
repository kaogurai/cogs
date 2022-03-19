import contextlib
import random
import urllib

import discord
from redbot.core import commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta


class TextMixin(MixinMeta):
    @commands.command(aliases=["definition", "synonym", "antonym"])
    async def define(self, ctx, *, thing_to_define: str):
        """Define a word or phrase."""
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(thing_to_define)}"
        async with self.session.get(url) as resp:
            if resp.status == 404:
                await ctx.send("I couldn't find a definition for that.")
                return
            if resp.status != 200:
                await ctx.send("Something went wrong when trying to get the definition.")
                return
            data = await resp.json()
        embeds = []
        for i, result in enumerate(data):
            embed = discord.Embed(color=await ctx.embed_color())
            if "partOfSpeech" in result["meanings"][0]:
                embed.title = (
                    f"{result['word']} ({result['meanings'][0]['partOfSpeech']})"
                )
            else:
                embed.title = result["word"]
            embed.description = result["meanings"][0]["definitions"][0]["definition"]
            if (
                "example" in result["meanings"][0]["definitions"][0]
                and result["meanings"][0]["definitions"][0]["example"]
            ):
                embed.add_field(
                    name="Example",
                    value=result["meanings"][0]["definitions"][0]["example"],
                )
            if (
                "synonyms" in result["meanings"][0]["definitions"][0]
                and result["meanings"][0]["definitions"][0]["synonyms"]
            ):
                embed.add_field(
                    name="Synonyms",
                    value=", ".join(result["meanings"][0]["definitions"][0]["synonyms"]),
                )
            if (
                "antonyms" in result["meanings"][0]["definitions"][0]
                and result["meanings"][0]["definitions"][0]["antonyms"]
            ):
                embed.add_field(
                    name="Antonyms",
                    value=", ".join(result["meanings"][0]["definitions"][0]["antonyms"]),
                )
            if len(data) > 1:
                embed.set_footer(text=f"Result {i + 1}/{len(data)}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command()
    async def translate(self, ctx, lang_code: str, *, text: str):
        """
        Translate text to a language.

        `lang_code` is the language code for the language you want to translate to.
        """
        url = f"{self.KAO_API_URL}/various/translate?result_language_code={lang_code[:10]}&text={urllib.parse.quote(text)}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                await ctx.send("Something went wrong when trying to translate.")
                return
            data = await resp.json()
        embed = discord.Embed(
            color=await ctx.embed_color(),
            title="Translation",
            description=data["text"][:4000],
        )
        await ctx.send(embed=embed)

    # Truth Source
    # https://raw.githubusercontent.com/zjulia/TruthOrDare/master/English%20Database.txt
    @commands.command()
    async def truth(self, ctx):
        """Get a truth question for truth and dare."""
        truths = [
            "Who was your first crush?",
            "What was the worst grade that you got this year?",
            "What do you do in your free time that nobody knows that you do?",
            "Is your underwear boring or do they have pictures and words on them?",
            "Do you match your underwear to your outfit?",
            "How much time do you spend getting ready every day?",
            "Why do or don't you wear makeup?",
            "Do you eat differently in front of people than you do by yourself?",
            "Do you like the 'nice guys' or the 'bad boys'?",
            "Do you care about what goes on in the rest of the world?",
            "Do you know where France is located on a map? Where's Italy?",
            "Have you ever been scared for your life?",
            "Where did that scar come from?",
            "Would you ever mercy kill someone?",
            "How do you imagine your wedding?",
            "How many people do you think you'll date before you marry? How many do you want to?",
            "Can you fall in love with two people at the same time?",
            "What is your goal in life?",
            "What do you think the person to your right thinks about you?",
            "How do you think other people perceive you?",
            "What do you think of yourself?",
            "Are you happy with your life choices?",
            "Do you believe in fate or destiny?",
            "If you had to kill everyone in this room OR kill yourself, which would you choose?",
            "Who do you think about the most?",
            "What was your first impression of the person to your left?",
            "Why do you like your crush?",
            "What determines if you will be friends with someone",
            "What do you look for in a friend?",
            "How often do you lie in this game?",
            "What is the worst gift you have ever received?",
            "What is the meanest thing you've ever done? Would you do it again?",
            "Have you ever cheated to win a game?",
            "Have you ever cheated on a test or homework?",
            "Who is the ugliest person you know?",
            "Have you ever talked bad about someone in the room?",
            "What is one annoying habit of each person in the room?",
            "Have you ever lied to a teacher? If so, what was it about?",
            "What was the worst grade you ever got?",
            "Have you ever broken something that belonged to someone else and not told them?",
            "Have you ever pretended to be sick or busy to avoid seeing someone in the room?",
            "Do you sleep with a night light or stuffed animal?",
            "What is your spirit animal?",
            "How many kids do you want to have?",
            "What is your guilty pleasure TV show?",
            "When you get a text, who do you hope it's from?",
            "What do you think your friends dislike about you the most?",
            "What was the worst day of your life?",
            "Have you ever accidentally started a rumour and then let it keep going?",
            "If you had to relive the same year forever that you've already lived, which year would you choose?",
            "Do you believe in a God? Are you sure?",
            "What kind of underwear do you wear?",
            "Tell us about your first kiss, if you haven't had one yet, tell us how you want it to go down.",
            "Have you ever seen a naked person before?",
            "If drugs were legal, would you do them?",
            "If all crime was legal for one day, what would you do?",
            "Have you ever lied to your parents? About what?",
            "When was the last time someone called you out on a lie?",
            "Have you lied during this game?",
            "If you were the opposite gender for a day, what would you do?",
            "What TV show or movie are you emabarrased for watching or liking?",
            "Who in this room would be the worst person to be stuck in an elevator with?",
            "Are you even a little bit racist?",
            "When you tell people your grade/gpa/etc., do you round up or down? Or not at all?",
            "Have you ever lied to make someone feel better? About what?",
            "Who is the meanest person in the room?",
            "Who in the room do you like the least",
            "Who in the room would you like to go on a date with?",
            "Who would you die for?",
            "Who would you take a bullet for but not die for?",
            "What do you do to make some money?",
            "What would you give all your money to have?",
            "Is there an afterlife? What do you think it is like? What do you want it to be like?",
            "If you are religious, what would you do differently in your life if you found out for sure that there was no God? If you are not religious, what would you do differently in your life if you found out for sure that was is a God?",
            "If you could be a different ethnicity, would you want to change?",
            "Do you believe there is life out there?",
            "What would be your personal Hell?",
            "What scares you in the dark?",
            "What would you be afraid of more if you were alone in a dark forest, bugs/murderers or ghosts/monsters?",
            "Who do you dress up for? Who do you try to impress?",
            "Have you had any life changing events? If so, what was it?",
            "What do people think that you would like but you actually hate?",
            "What traditional gender roles do you agree with?",
            "Which stereotypes do you think are actually true?",
            "On days that nobody sees you and you can stay home, what do you do differently?",
            "What do you do to try and impress your crush",
            "What is the stupidest thing you've had a fight about?",
            "What bad habit do you have that you want to break?",
            "Have you ever done something and then blamed it on someone else?",
            "Who do you think tried to impress you?",
            "If you were morbidly obese, would you want people to tell you and try to help you or leave you alone and let you live your life?",
            "What is your favorite bad word?",
            "What is your earliest memory?",
            "If you had all the money in the world, would you still go to college? What would you major in?",
            "Who is the worst person you know?",
            "What would you do if you found out your child was a bully?",
            "What would you do if you found our your parent was a bully at work?",
            "Who is your dearest friend?",
            "What is your most prized possession?",
            "If this room caught on fire, what things would you try to save?",
            "If you could only eat one food for the rest of your life, what would it be?",
            "When you argue and you realize you're wrong, do you keep arguing or admit defeat?",
            "If you had one hour everyday for which you were invisible, what would you do?",
            "If you could be famous for something, what would you want it to be for?",
            "If you could make the same amount of money being a world-renown doctor/scientist or a famous swimsuit model, which would you be?",
            "What would you rather be doing right now?",
            "Do you secretly not want to play this game any more?",
            "Would you or have you flirted with a cashier to get a discount?",
            "How many different passwords do you have?",
            "Who in the room would you want to switch parents or siblings with?",
            "What features do you looks for in a mate? What about in a friend?",
            "Have you ever had a now or never moment?",
            "What are you doing in school that you think is the least useful in life?",
            "Do you have a signature? How did you create it?",
            "What's more important in a food? How it looks, smells, or tastes?",
            "Have you cried in public?",
            "What is the least amount of stuff you would need to be happy?",
            "What songs do you listen to when you're sad?",
            "What is a secret that you promised to keep but then didn't?",
            "Does your best friend call you their best friend?",
            "What rule do you regularly break?",
            "What do you hate about your life?",
            "What do you love about your life?",
            "Who is the smartest person in the room?",
            "If you could trade half your IQ to be the most beautiful person in the world, would you do it?",
            "In what scenario would you die for someone else?",
            "Who would you die for?",
            "Who would die for you?",
            "Who in the room would you take a bullet for but not die for?",
            "Do you have a crush on another player?",
            "Is this game boring you?",
            "Is there anyone that is playing that you don't like but pretend to be friends with?",
            "What is the best lie that you have ever pulled off?",
            "Who do you think has lied in this game?",
            "Who do you wish was here?",
            "What were you afraid of when you were little that you aren't afraid of now?",
            "What were you afraid of when you were little that you are still afraid of now?",
            "What is the most illegal thing that you want to do?",
            "If you could change one thing about yourself, what would it be?",
            "If you could change one thing about the person to your right, what would it be?",
            "Do you think you're attractive?",
            "Have you ever done anything illegal?",
            "Who is your current crush?",
            "What do you really think about the person sitting to your right?",
            "What are your biggest insecurities?",
            "Who do you wish you could be?",
            "How much would you pay for the person to your left if they were held for ransom?",
            "What would you do for a Klondike Bar?",
            "Who do you regularly stalk on Facebook?",
            "What do people dislike about you the most?",
            "What do people like about you the most?",
            "What is a deal breaker for you?",
            "What would be your ideal date?",
            "What is your worst fear?",
            "What was the last thing you remember dreaming about?",
            "When was the last time you lied and what was it about?",
            "What is the meanest thing you've done and do you regret it?",
            "Have you ever cheated? Who what when where why.",
            "What is the craziest thing you've done to get your crush's attention",
            "What is your biggest regret?",
            "What is the funniest thing that has ever happened to you?",
            "Have you ever stolen anything?",
            "When was the last time someone saw you naked?",
            "When was the last time you farted?",
            "Have you ever fallen for someone your shouldn't have? Who what when where why.",
            "How long have you gone without showering or brushing your teeth?",
            "Do you floss?",
        ]
        await ctx.send(random.choice(truths))

    # Dare Source
    # https://raw.githubusercontent.com/zjulia/TruthOrDare/master/English%20Database.txt
    @commands.command()
    async def dare(self, ctx):
        "Get a dare for a game of truth and dare."
        dares = [
            "Fake a marriage proposal.",
            "I dare you to face a fear",
            "Take a shot of ketchup",
            "Cover your face entirely in ketchup like a mask until it dries",
            "Act out the death scene in Romeo and Juliet where you're both people",
            "Make the frowniest face that you can and do an evil laugh",
            "Break dance",
            "Call your crush and ask to talk to their parents, have a conversation",
            "Call your crush and say that you like someone else",
            "Call your crush and tell them that you heard they like you",
            "Eat a piece of dog or cat food",
            "Try to scratch your armpit with your toe",
            "Call a random number and make weird noises when they answer",
            "Call a random number and pretend to be their kid",
            "Call a random number and ask if their refrigerator is running, if they say yes then say that they should go catch it",
            "Call a random number and try to sell them something.",
            "Wax something.",
            "Make an angry face and keep it for 60 seconds",
            "Make a really weird face and go talk to someone not in the group",
            "Act out a death scene",
            "Brush the teeth of the person who next picks a dare",
            "Brush the teeth of the person who last got dared",
            "Go into as far of a split as you can do",
            "Try to do a cartwheel",
            "Dip your hands in the toilet",
            "Snort like a pig for 30 seconds",
            "Run around the yard acting like a horse",
            "Dance like a cow boy",
            "Do a model runway walk down the hall",
            "Call your crush and try to sell him a potato",
            "Call your crush and tell them you like them, now or never",
            "Find a couple in public and say 'I thought we had something special!' and run away pretending to cry",
            "Have the person to your right do your hair however they want and leave it that way until the end of the game",
            "Smell the feet of everyone in the room and rank them from best to worst",
            "Read the last text that you received out loud",
            "Use someone else's phone and prank call your mom",
            "Do an imitation of the person on your right",
            "Repeat everything anyone says until the next dare",
            "Say the pledge of allegiance in slow motion",
            "Call your sibling or parent if you don't have a sibling and tell them how great they are",
            "Drink some toilet water",
            "Convince a parent that you just failed a test",
            "Convince a parent that you were caught cheating on a test and they have to pay a $250 fine or you'll be kicked out of school",
            "Do the chicken dance",
            "Call your parents and tell them that you were dared to drive the car and then you crashed it",
            "Call your parents and tell them that you were dared to do drugs and now you don't know where you are or what happened",
            "Try not to smile while all other players try to make your smile by any means necessary.",
            "Touch your nose with your tongue, if you can't, you have to touch someone else's nose with your tongue.",
            "Have another player select a food item from the kitchen for you to eat without using your hands.",
            "Poke someone you don't really know on Facebook",
            "If in public, go up to a stranger and pretend to know them.",
            "Every time the player to your left says something, you have to say 'All hail Queen/King' and then their name until you get another dare.",
            "Log into your Facebook and allow other players to do whatever they want for 60 seconds. Anything done cannot be undone.",
            "Update your Facebook status to say that you are single and ready to mingle.",
            "Slow dance with someone while blindfolded and try to guess who they are without them speaking.",
            "Try to get the person next to you to laugh while they are trying not to laugh.",
            "Make out with a piece of fruit.",
            "Walk around outside in your pajamas.",
            "Put makeup on yourself while blindfolded.",
            "Put makeup on someone else while blindfolded.",
            "Hug someone of the opposite gender.",
            "Hug someone of the same gender.",
            "Talk like Shakespeare for a while.",
            "Fake a pregnancy to your parents.",
            "Call a random number and pretend to be their long lost friend from that time ago.",
            "Call a random number and try to order a pizza ... in a funny accent.",
            "Speak in an Australian accent until your next turn.",
            "Imitate someone in the room.",
            "Imitate a teacher",
            "Imitate a celebrity.",
            "Perform a 15 second long belly dance in the center of the room.",
            "Sing a song and make up movements for it.",
            "Prank call a random number.",
            "Call a friend's mom and tell them they need to lose weight.",
            "If in a public location, pick a stranger and ask them out.",
            "Brush your teeth with a bottle of Jack ... or orange juice.",
            "Brush your teeth with your non-dominant hand.",
            "Call your crush and ask them out on a date.",
            "Crack an egg on your head in front of a parent with no explanation.",
            "Close your eyes until your next turn.",
            "Make out with your elbow.",
            "Drink some ketchup.",
            "Piggyback someone until your next turn.",
            "Let everyone draw on your face for 10 seconds.",
            "Slap a piece of bologna or cheese onto your face and leave it there until your next dare.",
            "Put a cookie on your forehead and try to eat it without getting help or using your hands.",
            "Wear someone's socks on your hands until their next dare.",
            "Sing a song chosen by the person who previously chose a dare.",
            "Have someone put makeup on your while they are blindfolded.",
            "Stand in the toilet bowl and flush.",
            "Go on Facebook, message the first name you see and tell them that you have secretly been in love with them for the past 5 years.",
            "Have a slow motion fight with an imaginary dragon.",
            "Go around the place slapping your bare belly for one minute.",
            "Act like a farm animal for 15 seconds.",
            "Eat a spoonful of mayo.",
            "Pick a song and then make up your own words to ten seconds of it.",
            "Lick the mirror (and then clean it cuz that's gross).",
            "Pretend to be a sumo wrestler for one minute, have an imaginary fight",
            "Stuff your mouth with marshmallows and say 'chubby bunny' 10 times.",
            "Try to do a hand stand.",
            "Try to do a cart wheel.",
            "Slow dance with an imaginary partner.",
            "Do an imitation of Shrek.",
            "Do an imitation of Obama.",
            "Put your arms in your armpits and flap your wings around the house.",
            "Make rooster noises until someone comes into the room to ask if you're ok.",
        ]
        await ctx.send(random.choice(dares))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(mention_everyone=True)
    async def forcemention(self, ctx, role: discord.Role, *, message: str = None):
        """Force mention a role with an optional message."""
        m = f"{role.mention}\n{message[:2000]}" if message else role.mention
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            with contextlib.suppress(discord.NotFound):
                await ctx.message.delete()
        if (
            not role.mentionable
            and not ctx.channel.permissions_for(ctx.guild.me).mention_everyone
            and ctx.guild.me.top_role > role
        ):
            await role.edit(mentionable=True)
            await ctx.channel.send(
                m, allowed_mentions=discord.AllowedMentions(roles=True)
            )
            await role.edit(mentionable=False)
        else:
            await ctx.channel.send(
                m, allowed_mentions=discord.AllowedMentions(roles=True)
            )
