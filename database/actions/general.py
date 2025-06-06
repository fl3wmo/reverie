import datetime
import typing

import discord
from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

from database.actions.action import Act, action
from info.punishments import hints_to_definitions

if typing.TYPE_CHECKING:
    from core.bot import Reverie


class Actions:
    def __init__(self, collection: MotorCollection):
        self._collection = collection
        self.reasons_cache: dict[(int, int), list[str]] = {}

    async def get(self, act_id: int) -> Act:
        return Act(**await self._collection.find_one({'id': act_id}))

    async def by_user(self, user: int, *, guild: typing.Optional[int] = None, counting: bool = False, after: datetime.datetime = None) -> list[Act]:
        query = {'user': user}
        if guild:
            query['guild'] = guild
        if counting:
            query['counting'] = True
        if after:
            query['at'] = {'$gte': after}
            query['reason'] = {'$ne': None}
        return [Act(**doc) async for doc in self._collection.find(query)]

    async def by_moderator(self, moderator: int, *, counting: bool = False, guild: int = None,
                           date_from: datetime.datetime = None, date_to: datetime.datetime = None) -> list[Act]:
        query = {'moderator': moderator}
        if guild:
            query['guild'] = guild
        if date_from:
            date_from = date_from.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(hours=3)
            if date_to:
                date_to = date_to.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(hours=3)
            query['at'] = {'$gte': date_from,
                           '$lt': (date_from + datetime.timedelta(days=1) if not date_to else date_to)}
        if counting:
            query['counting'] = True
        return [Act(**doc) async for doc in self._collection.find(query)]

    async def record(
            self, user: int, guild: int,
            moderator: int, action_type: action, *,
            counting: bool = True, duration: float = None,
            reason: str = None, prove_link: str = None,
            auto_review: bool = False
    ) -> Act:
        if reason and 'not_pick' in reason:
            raise ValueError(
                '### Вы ввели некорректную причину.\nВозможно, вы нажали не туда?\n-# Не нажимайте на названия категорий\n-# Попробуйте **ввести название категории** вручную и тогда **выбрать из предложенных**.')
        if reason:
            reason = hints_to_definitions(reason)
            if (guild, user) in self.reasons_cache:
                self.reasons_cache[(guild, user)].append(reason)

        if 'role' not in action_type and 'remove' in action_type:
            last_act = await self.last_act(user, guild, str(action_type).replace('remove', 'give'))
            if last_act:
                await self.deactivate(last_act.id, moderator)

        act_id = (await self._collection.count_documents({})) + 1
        act = Act(
            id=act_id,
            at=datetime.datetime.now(datetime.UTC),
            user=user,
            guild=guild,
            moderator=moderator,
            reviewer=moderator if auto_review else None,
            type=action_type,
            counting=counting,
            duration=duration,
            reason=reason,
            prove_link=prove_link
        )
        await self._collection.insert_one(act.as_dict)
        return act

    async def set_prove_link(self, act_id: int, link: str) -> None:
        await self._collection.update_one({'id': act_id}, {'$set': {'prove_link': link}})

    async def last_act(self, user: int, guild: int, action_type: action) -> Act | None:
        act = await self._collection.find_one({'user': user, 'guild': guild, 'type': action_type, 'counting': True}, sort=[('id', -1)])
        if act is None:
            return None
        return Act(**act)

    async def deactivate(self, act_id: int, reviewer: int) -> None:
        act = await self.get(act_id)
        if (act.guild, act.user) in self.reasons_cache:
            self.reasons_cache[(act.guild, act.user)].remove(act.reason)
        await self._collection.update_one({'id': act_id}, {'$set': {'reviewer': reviewer, 'counting': False}})

    async def approve(self, act_id: int, reviewer: int, client: 'Reverie' = None,
                      interaction: discord.Interaction = None) -> None:
        act = await self.get(act_id)
        if 'ban' in act.type and 'give' in act.type:
            bans = client.get_cog('ban')
            await bans.on_approve(act_id)
        elif 'warn' in act.type:
            warns = client.get_cog('warn')
            if 'give' in act.type:
                member, user = await client.getch_any(interaction.guild, act.user, interaction.user)
                await warns.on_approve(interaction, act_id, user)
            elif 'remove' in act.type:
                await warns.on_remove_approve(act_id)
        await self._collection.update_one({'id': act_id}, {'$set': {'reviewer': reviewer}})

    async def similar(self, guild_id: int) -> list[Act]:
        pipeline = [
            {'$match': {'guild': guild_id}},
            {'$group': {
                '_id': {'user': '$user', 'moderator': '$moderator'},
                'count': {'$sum': 1}
            }},
            {'$match': {'count': {'$gt': 1}}}
        ]
        results = [doc async for doc in self._collection.aggregate(pipeline)]
        query = {'$or': [{'user': doc['_id']['user'], 'moderator': doc['_id']['moderator']} for doc in results]}
        return [Act(**doc) async for doc in self._collection.find(query)] if results else []

    async def reasons_history(self, user_id: int, guild_id: int) -> list[str]:
        if (cache := self.reasons_cache.get((guild_id, user_id))) is not None:
            return cache

        all_acts = await self.by_user(user_id, guild=guild_id, counting=True, after=datetime.datetime.now() - datetime.timedelta(days=30))
        self.reasons_cache[(guild_id, user_id)] = [act.reason for act in all_acts if act.reason]
        return self.reasons_cache[(guild_id, user_id)]