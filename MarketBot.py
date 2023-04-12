import discord
from discord.ext import commands
from discord import option
import easybcc
import json
import uuid

token = ''

with open('../tokens/market_token.txt', 'r') as file:
    token = file.read().rstrip()

bcc_session = easybcc.easy_bcc(False)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='$', intents=intents)

bot_data = {}

usr_carts = {}


products_json_base = {
    "product_id" : "",
    "product_name" : "",
    "product_desc" : "",
    "product_price" : 0.0,
    "msg_id" : 0
    }

store_json_base = {
    "store_id" : "",
    "store_channel" : 0,
    "store_cur" : "",
    "products" : []
    }

guild_json_base = {
                    "cmd_channel" : 0,
                    "bcc_token" : "",
                    "bcc_endpoint" : "",
                    "bcc_store_id" : "",
                    "receipt_channel" : 0,
                    "webhook_url" : "",
                    "owner" : "",
                    "admins" : [],
                    "stores" : [],
                    "init" : False,
                    "active_invoices" : {}
                    }

class ProductButtons(discord.ui.View): 
    
    def __init__(self, product_id, store_id):
        self.prod_id = product_id
        self.store_id = store_id
    
    @discord.ui.button(label="Add to Cart", row=0, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, button, interaction):
        for store in bot_data[interaction.guild_id]:
            if store["store_id"] == self.store_id:
                for prod in store["products"]:
                    if prod["product_id"] == self.product_id:
                        usr_carts[interaction.user.id][self.store_id][self.product_id] = usr_carts[interaction.user.id][self.store_id][self.product_id] + 1
                        prod_name = prod["product_name"]
                        await interaction.response.send_message(f"Added one {prod_name} to your cart")
                        break
                break
            
    @discord.ui.button(label="Remove From Cart", row=1, style=discord.ButtonStyle.danger)
    async def second_button_callback(self, button, interaction):
        for store in bot_data[interaction.guild_id]:
            if store["store_id"] == self.store_id:
                for prod in store["products"]:
                    if prod["product_id"] == self.product_id:
                        usr_carts[interaction.user.id][self.store_id][self.product_id] = usr_carts[interaction.user.id][self.store_id][self.product_id] - 1 if usr_carts[interaction.user.id][self.store_id][self.product_id] > 0 else 0
                        prod_name = prod["product_name"]
                        await interaction.response.send_message(f"Removed one {prod_name} to your cart")
                        break
                break
            
class CheckoutView(discord.ui.View):
    
    def __init__(self, store_id, usr_id, cost):
        self.target_usr = usr_id
        self.store_id = store_id
        self.price = cost
        
    @discord.ui.button(label="Checkout", style=discord.ButtonStyle.success)
    async def button_callback(self, button, interaction):
        if interaction.user.id != self.target_usr:
            await interaction.response.send_message("This is not your cart.")
            return
        button.disabled = True
        endpoint = bot_data[interaction.guild_id]["bcc_endpoint"]
        token = bot_data[interaction.guild_id]["bcc_token"]
        bcc_store_id = bot_data[interaction.guild_id]["bcc_store_id"]
        notif_url = bot_data[interaction.guild_id]["webhook_url"]
        cur = None
        
        for store in bot_data[interaction.guild_id]:
            if store["store_id"] == self.store_id:
                cur = store["store_cur"]
        
        inv_data = bcc_session.gen_invoice(endpoint, token, bcc_store_id, self.price, cur, notif_url)
        ##future implementation would allow user to choose which crpyto they pay with instead off getting all payment URIs
        local_receipt_msg = "Payment Receipt:\n"
        for payment in inv_data["payments"]:
            local_receipt_msg = local_receipt_msg + f"{payment['name']}\nAmount: {payment['amount']}\nRecommended Fee: {payment['recommended_fee']}\nAddress: {payment['payment_address']}\nPayment URL: {payment['payment_url']}\n\n"
        
        await interaction.user.send(local_receipt_msg)
        await interaction.guild.get_channel(int(bot_data[interaction.guild.id]["receipt_channel"])).send(local_receipt_msg)
        bot_data[interaction.guild.id]["active_invoices"][interaction.user.id].append(payment["id"])
        await interaction.response("Payment receipt has been DM'd!")
        
with open('bot_data.json', 'r') as f:
    bot_data = json.load(f)

def save_bot():
    with open('bot_data.json', 'w') as f:
        f.seek(0)
        json.dump(bot_data, f)
        f.truncate()

def bot_owner_only():
    async def predicate(ctx):
        return await bot.is_owner(ctx.author)
    return commands.check(predicate)

def guild_owner_only():
    async def predicate(ctx):
        return ctx.author == ctx.guild.owner
    return commands.check(predicate)

def cmd_channel_only():
    async def predicate(ctx):
        return ctx.channel.id == int(bot_data[ctx.guild.id]["cmd_channel"])
    return commands.check(predicate)
        
    
def admin_only():
    async def predicate(ctx):
        return True if ctx.author.id in bot_data[ctx.guild.id]["admins"] else False
    return commands.check(predicate)
    
def market_channel_only():
    async def predicate(ctx):
        for store in bot_data[ctx.guild.id]["stores"]:
            if ctx.channel.id == store["store_channel"]:
                return True
        return False
    return commands.check(predicate)
    
def guild_init_only():
    async def predicate(ctx):
        return bot_data[ctx.guild.id]["init"]
    return commands.check(predicate)
    
@bot.command(name="reconfig", description="Debugging command only.")
@bot_owner_only()
async def reconfig(ctx):
    bot_data[ctx.guild.id] = guild_json_base.copy()
    bot_data[ctx.guild.id]["owner"] = ctx.guild.owner.id
    bot_data[ctx.guild.id]["admins"].append(ctx.guild.owner.id)
    save_bot()
    await ctx.send("Initial JSON Reset.")

@bot.command(name="ping", description="A command to make sure the bot is listening to the server")
@guild_owner_only()
async def alive_test(ctx):
    await ctx.send("Hello world!")
    
@bot.event
async def on_ready():
    print("MarketBot is online!")

@bot.event
async def on_guild_join(guild):
    bot_data[guild.id] = guild_json_base.copy()
    bot_data[guild.id]["owner"] = guild.owner.id
    bot_data[guild.id]["admins"].append(guild.owner.id)
    save_bot()
    
@bot.event
async def on_guild_remove(guild):
    del bot_data[guild.id]
    save_bot()

@bot.slash_command(name="set_cmd_channel", description="Sets the channel that the bot will perform admin commands in")
@guild_owner_only()
async def set_cmd_channel(ctx):
    bot_data[ctx.guild.id]["cmd_channel"] = ctx.channel.id
    save_bot()
    await ctx.respond("Admin commands will only be usuable in this channel now.")
    
@bot.command(name="add_admin", description="Adds admins from mentions")
@guild_owner_only()
@cmd_channel_only()
async def add_admin(ctx):
    if ctx.message.mentions:
        for usr in ctx.message.mentions:
            bot_data[ctx.guild.id]["admins"].append(usr.id)
        save_bot()
        await ctx.respond("Admins added.")
    else:
        await ctx.respond("You didn't mention anyone!")
        
@bot.command(name="rem_admin", description="Removes admins from mentions")
@guild_owner_only()
@cmd_channel_only()
async def rem_admin(ctx):
    if ctx.message.mentions:
        for usr in ctx.message.mentions:
                if usr.id in bot_data[ctx.guild.id]["admins"]:
                    bot_data[ctx.guild.id]["admins"].remove(usr.id)
        save_bot()
        await ctx.respond("Admins removed.")
    else:
        await ctx.respond("You didn't mention anyone!")
        
@bot.slash_command(name="configure_market", description="Configures the market. This is necessary for the bot to be initialized within your server.")
@option("bcc_token", str, description="The access token to your BitcartCC instance", required=True)
@option("bcc_endpoint", str, description="The endpoint of your BitcartCC instance. I.e. yourdomain.tld/api", required=True)
@option("bcc_store_id", str, description="The ID of the store you're accessing. Currently support is one store per guild.", required=True)
@option("bcc_receipt_channel", str, description="The ID of the channel that invoice notifications should go to.", required=True)
@admin_only()
@cmd_channel_only()
async def config(ctx, bcc_token : str , bcc_endpoint : str, bcc_store_id : str, receipt_channel : str):
    bot_data[ctx.guild.id]["bcc_token"] = bcc_token
    bot_data[ctx.guild.id]["bcc_endpoint"] = bcc_endpoint
    bot_data[ctx.guild.id]["bcc_store_id"] = bcc_store_id
    #####webhook setup#####
    #####make a webhook on the specified channel#####
    #####this webhook is pased to the invoice generator#####
    #####when triggered the bot should process the invoice, but that is a separate method####
    webhook = await ctx.guild.get_channel(int(receipt_channel)).create_webhook(name="Receipt Webhook")
    bot_data[ctx.guild.id]["webhook_url"] = webhook.url
    
    stats_rep = bcc_session.get_stats(bcc_endpoint,bcc_token)
    if stats_rep.status_code == 200:
        bot_data[ctx.guild.id]["init"] = True
        save_bot()
        await ctx.respond("Configured successfully!")
    else:
        await ctx.respond("Configuration failed. Please check your token can check the statistics of your store, and the endpoint it valid!")

@bot.slash_command(name="add_market", description="Adds a market to a specified channel.")
@option("channel_id", str, description="The channel that this store will be active in.", required=True)
@option("currency", str, description="The currency to be used for price calculations", required=True)
@guild_init_only()
@admin_only()
@cmd_channel_only()
async def new_market(ctx, channel_id : str, cur : str):
    n_store = store_json_base.copy()
    n_store["store_id"] = str(uuid.uuid4().hex())
    n_store["store_channel"] = int(channel_id)
    n_store["store_cure"] = cur
    await ctx.response("Created a new market!")
    await ctx.guild.get_channel(int(channel_id)).send(f"This channel is being used for store {n_store['store_id']}")

@bot.slash_command(name="add_product", description="Add product to store")
@option("store_id", str, description="The ID of the store to add this product to", required=True)
@option("product_name", str, description="Name of the product", required=True)
@option("product_desc", str, description="Description of the product", required=True)
@option("price", float, description="Price in the units of the store", required=True)
@guild_init_only()
@admin_only()
@cmd_channel_only()
async def add_product(ctx, store_id : str, product_name : str, product_desc : str, price : float):
    for store in bot_data[ctx.guild.id]["stores"]:
        if store["store_id"] == store_id:
            p_dat = products_json_base.copy()
            p_dat["product_id"] = str(uuid.uuid4().hex())
            p_dat["product_name"] = product_name
            p_dat["product_desc"] = product_desc
            p_dat["product_price"] = price
            p_dat["msg_id"] = await ctx.guild.get_channel(store["store_channel"]).send(f"{product_name}\n{product_desc}\n\n{price}", view=ProductButtons(p_dat["product_id"], store_id)).id
            store["products"].append(p_dat)
            await ctx.respond(f"Product {p_dat['product_id']} has been added to the store.")
            return
    await ctx.response("Store not found")
    
        
@bot.slash_command(name="product_man", description="Product management")
@option("store_id", str, description="The ID of the store to add this product to", required=True)
@option("operation", str, description="edit/remove", required=True)
@option("product_id", str, description="The ID of the product to be managed", required=True)
@option("product_name", str, description="Name of the product", required=False)
@option("product_desc", str, description="Description of the product", required=False)
@option("price", float, description="Price in the units of the store", required=False)
@guild_init_only()
@admin_only()
@cmd_channel_only()
async def product_management(ctx, store_id, op, prod_id, prod_name, prod_desc, price):
    for store in bot_data[ctx.guild.id]["stores"]:
        if store["store_id"] == store_id:
                for prod in store["products"]:
                    if prod["product_id"] == prod_id:
                        if op == "remove" or op == "rem":
                            store["products"].remove(prod)
                            await ctx.response("Product removed.")
                            return
                        elif op == "edit":
                            prod["product_name"] = prod_name or prod["product_name"]
                            prod["product_desc"] = prod_desc or prod["product_desc"]
                            prod["product_price"] = price or prod["product_price"]
                            await ctx.guild.get_channel(store["store_channel"]).fetch_message(prod["msg_id"]).edit(content=f"{prod['product_name']}\n{prod['product_name']}\n\n{prod['product_name']}")
                            await ctx.response("Product updated.")
                            return
                        else:
                            await ctx.response("Unknown operation. Options are: remove,edit")
                            return
                await ctx.response("Product not found.")
                return

@bot.slash_command(name="check", description="check cart or check out based on current market channel")
@option("operation", str, description="out", require=False)
@guild_init_only()
@market_channel_only()
async def check(ctx, op):
    for store in bot_data[ctx.guild.id]["stores"]:
        if store["store_channel"] == ctx.channel.id:
            cart_msg = "User cart:\n"
            running_cost = 0.0
            for products in usr_carts[ctx.author.id][store["store_id"]]:
                for product_id,count in products:
                    for product in store["products"]:
                        if product["product_id"] == product_id:
                            cart_msg = cart_msg + f"{product['product_name']}.............x{count}.........{product['product_price'] * count}\n"
                            running_cost = running_cost + product["product_price"] * count
            cart_msg = cart_msg + f"Total Cost..........................{running_cost}"
            await ctx.response(cart_msg, view=CheckoutView(store["store_id"],ctx.author.id,running_cost))
            break

# @bot.event
# async def on_message(msg):
#     await bot.process_commands(msg)
#     if msg.channel.id == bot_data[msg.guild.id]["receipt_channel"] :
#         if msg.webhook_id:
#             print(msg)
#             print("webhook test.")
            
bot.run(token)

#####https://discordapp.com/oauth2/authorize?&client_id=1095282314201792594&scope=bot&permissions=536947712
