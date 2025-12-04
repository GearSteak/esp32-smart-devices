"""
TTRPG Reference Data

Contains SRD (System Reference Document) content for D&D 5e
and Shadowdark, plus Open5e API integration.
"""

import json
import os
import requests
from typing import Optional, List, Dict

# Cache directory
CACHE_DIR = os.path.expanduser('~/.piwrist_ttrpg_cache')


# ============================================================
# D&D 5e SRD Data (Creative Commons)
# ============================================================

DND5E_SPELLS = {
    # Cantrips
    'fire_bolt': {
        'name': 'Fire Bolt',
        'level': 0,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': '120 feet',
        'duration': 'Instantaneous',
        'description': 'You hurl a mote of fire at a creature or object within range. Make a ranged spell attack. On hit, target takes 1d10 fire damage. Damage increases at 5th (2d10), 11th (3d10), and 17th level (4d10).'
    },
    'light': {
        'name': 'Light',
        'level': 0,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': 'Touch',
        'duration': '1 hour',
        'description': 'You touch one object no larger than 10 feet. It sheds bright light in 20-foot radius and dim light for additional 20 feet. Can be colored. Covering it blocks light.'
    },
    'mage_hand': {
        'name': 'Mage Hand',
        'level': 0,
        'school': 'Conjuration',
        'casting_time': '1 action',
        'range': '30 feet',
        'duration': '1 minute',
        'description': 'A spectral hand appears at a point you choose. It can manipulate objects, open doors, retrieve items. Cannot attack, activate magic items, or carry more than 10 pounds.'
    },
    'prestidigitation': {
        'name': 'Prestidigitation',
        'level': 0,
        'school': 'Transmutation',
        'casting_time': '1 action',
        'range': '10 feet',
        'duration': 'Up to 1 hour',
        'description': 'Minor magical trick. Create sensory effect, light/snuff flame, clean/soil object, chill/warm/flavor material, make symbol appear, create trinket or illusory image.'
    },
    'sacred_flame': {
        'name': 'Sacred Flame',
        'level': 0,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': '60 feet',
        'duration': 'Instantaneous',
        'description': 'Flame descends on creature you can see. Target must succeed on DEX save or take 1d8 radiant damage. No benefit from cover. Damage increases at 5th, 11th, and 17th level.'
    },
    # 1st Level
    'magic_missile': {
        'name': 'Magic Missile',
        'level': 1,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': '120 feet',
        'duration': 'Instantaneous',
        'description': 'You create three glowing darts of magical force. Each dart hits a creature of your choice and deals 1d4+1 force damage. At higher levels: +1 dart per slot level above 1st.'
    },
    'shield': {
        'name': 'Shield',
        'level': 1,
        'school': 'Abjuration',
        'casting_time': '1 reaction',
        'range': 'Self',
        'duration': '1 round',
        'description': 'An invisible barrier of magical force appears and protects you. Until start of your next turn, you have +5 bonus to AC, including against triggering attack, and take no damage from magic missile.'
    },
    'cure_wounds': {
        'name': 'Cure Wounds',
        'level': 1,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': 'Touch',
        'duration': 'Instantaneous',
        'description': 'A creature you touch regains 1d8 + your spellcasting modifier hit points. No effect on undead or constructs. At higher levels: +1d8 per slot level above 1st.'
    },
    'detect_magic': {
        'name': 'Detect Magic',
        'level': 1,
        'school': 'Divination',
        'casting_time': '1 action',
        'range': 'Self',
        'duration': 'Concentration, up to 10 minutes',
        'description': 'You sense the presence of magic within 30 feet. Can use action to see faint aura around any visible magical creature or object and learn its school of magic.'
    },
    'healing_word': {
        'name': 'Healing Word',
        'level': 1,
        'school': 'Evocation',
        'casting_time': '1 bonus action',
        'range': '60 feet',
        'duration': 'Instantaneous',
        'description': 'A creature of your choice that you can see regains 1d4 + your spellcasting modifier hit points. No effect on undead or constructs. Higher levels: +1d4 per slot above 1st.'
    },
    'sleep': {
        'name': 'Sleep',
        'level': 1,
        'school': 'Enchantment',
        'casting_time': '1 action',
        'range': '90 feet',
        'duration': '1 minute',
        'description': 'Roll 5d8; the total is how many HP of creatures this spell can affect. Starting with lowest HP creature in 20-foot radius, each falls unconscious. Higher levels: +2d8 per slot above 1st.'
    },
    # 2nd Level
    'hold_person': {
        'name': 'Hold Person',
        'level': 2,
        'school': 'Enchantment',
        'casting_time': '1 action',
        'range': '60 feet',
        'duration': 'Concentration, up to 1 minute',
        'description': 'Choose a humanoid you can see. Target must succeed on WIS save or be paralyzed. It can repeat the save at end of each of its turns, ending the effect on a success.'
    },
    'misty_step': {
        'name': 'Misty Step',
        'level': 2,
        'school': 'Conjuration',
        'casting_time': '1 bonus action',
        'range': 'Self',
        'duration': 'Instantaneous',
        'description': 'Briefly surrounded by silvery mist, you teleport up to 30 feet to an unoccupied space that you can see.'
    },
    'scorching_ray': {
        'name': 'Scorching Ray',
        'level': 2,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': '120 feet',
        'duration': 'Instantaneous',
        'description': 'You create three rays of fire and hurl them at targets within range. Make a ranged spell attack for each ray. On hit, target takes 2d6 fire damage. Higher levels: +1 ray per slot above 2nd.'
    },
    # 3rd Level
    'fireball': {
        'name': 'Fireball',
        'level': 3,
        'school': 'Evocation',
        'casting_time': '1 action',
        'range': '150 feet',
        'duration': 'Instantaneous',
        'description': 'A bright streak flashes and blossoms into an explosion of flame. Each creature in 20-foot radius sphere must make DEX save. Takes 8d6 fire damage on failed save, half on success. Higher levels: +1d6 per slot above 3rd.'
    },
    'counterspell': {
        'name': 'Counterspell',
        'level': 3,
        'school': 'Abjuration',
        'casting_time': '1 reaction',
        'range': '60 feet',
        'duration': 'Instantaneous',
        'description': 'You attempt to interrupt a creature casting a spell. If the spell is 3rd level or lower, it fails. If higher, make ability check using your spellcasting ability (DC 10 + spell level).'
    },
    'dispel_magic': {
        'name': 'Dispel Magic',
        'level': 3,
        'school': 'Abjuration',
        'casting_time': '1 action',
        'range': '120 feet',
        'duration': 'Instantaneous',
        'description': 'Choose any creature, object, or magical effect within range. Any spell of 3rd level or lower on the target ends. For higher level spells, make spellcasting ability check (DC 10 + spell level).'
    },
}

DND5E_RACES = {
    'human': {
        'name': 'Human',
        'speed': 30,
        'size': 'Medium',
        'traits': [
            '+1 to all ability scores',
            'Extra language of your choice',
        ],
        'description': 'Humans are the most adaptable and ambitious people. They vary widely in appearance and have short lifespans compared to other races.'
    },
    'elf': {
        'name': 'Elf',
        'speed': 30,
        'size': 'Medium',
        'traits': [
            '+2 DEX',
            'Darkvision 60 ft',
            'Fey Ancestry (advantage vs charm, immune to magic sleep)',
            'Trance (4 hours instead of sleep)',
            'Perception proficiency',
        ],
        'description': 'Elves are a magical people of otherworldly grace. They love nature, magic, art, music, poetry, and the good things of the world.'
    },
    'dwarf': {
        'name': 'Dwarf',
        'speed': 25,
        'size': 'Medium',
        'traits': [
            '+2 CON',
            'Darkvision 60 ft',
            'Dwarven Resilience (advantage vs poison, resistance to poison damage)',
            'Stonecunning (History checks on stonework)',
            'Tool proficiency (smith, brewer, or mason)',
        ],
        'description': 'Bold and hardy, dwarves are known as skilled warriors, miners, and workers of stone and metal.'
    },
    'halfling': {
        'name': 'Halfling',
        'speed': 25,
        'size': 'Small',
        'traits': [
            '+2 DEX',
            'Lucky (reroll natural 1s on attacks, saves, checks)',
            'Brave (advantage vs frightened)',
            'Halfling Nimbleness (move through larger creatures)',
        ],
        'description': 'The diminutive halflings survive in a world full of larger creatures by avoiding notice or, barring that, avoiding offense.'
    },
}

DND5E_CONDITIONS = {
    'blinded': {
        'name': 'Blinded',
        'effects': [
            "Can't see, automatically fails checks requiring sight",
            'Attack rolls against creature have advantage',
            "Creature's attacks have disadvantage",
        ]
    },
    'charmed': {
        'name': 'Charmed',
        'effects': [
            "Can't attack the charmer or target them with harmful abilities/spells",
            'Charmer has advantage on social checks against the creature',
        ]
    },
    'frightened': {
        'name': 'Frightened',
        'effects': [
            'Disadvantage on ability checks and attacks while source of fear is in sight',
            "Can't willingly move closer to the source of fear",
        ]
    },
    'grappled': {
        'name': 'Grappled',
        'effects': [
            'Speed becomes 0',
            "Can't benefit from any bonus to speed",
            'Ends if grappler is incapacitated or moved apart',
        ]
    },
    'incapacitated': {
        'name': 'Incapacitated',
        'effects': [
            "Can't take actions or reactions",
        ]
    },
    'paralyzed': {
        'name': 'Paralyzed',
        'effects': [
            'Incapacitated, cannot move or speak',
            'Automatically fails STR and DEX saves',
            'Attacks against have advantage',
            'Hits from within 5 feet are critical hits',
        ]
    },
    'poisoned': {
        'name': 'Poisoned',
        'effects': [
            'Disadvantage on attack rolls and ability checks',
        ]
    },
    'prone': {
        'name': 'Prone',
        'effects': [
            'Only movement option is to crawl (costs extra movement)',
            'Disadvantage on attack rolls',
            'Attacks from within 5 feet have advantage, beyond have disadvantage',
        ]
    },
    'stunned': {
        'name': 'Stunned',
        'effects': [
            'Incapacitated, cannot move, can only speak falteringly',
            'Automatically fails STR and DEX saves',
            'Attacks against have advantage',
        ]
    },
    'unconscious': {
        'name': 'Unconscious',
        'effects': [
            'Incapacitated, cannot move or speak, unaware of surroundings',
            'Drops whatever held, falls prone',
            'Automatically fails STR and DEX saves',
            'Attacks have advantage, hits from 5 feet are crits',
        ]
    },
}

DND5E_ITEMS = {
    # === WEAPONS - Simple Melee ===
    'club': {
        'name': 'Club',
        'type': 'Simple Melee',
        'cost': '1 sp',
        'damage': '1d4 bludgeoning',
        'weight': '2 lb',
        'properties': ['Light'],
    },
    'dagger': {
        'name': 'Dagger',
        'type': 'Simple Melee',
        'cost': '2 gp',
        'damage': '1d4 piercing',
        'weight': '1 lb',
        'properties': ['Finesse', 'Light', 'Thrown (20/60)'],
    },
    'handaxe': {
        'name': 'Handaxe',
        'type': 'Simple Melee',
        'cost': '5 gp',
        'damage': '1d6 slashing',
        'weight': '2 lb',
        'properties': ['Light', 'Thrown (20/60)'],
    },
    'mace': {
        'name': 'Mace',
        'type': 'Simple Melee',
        'cost': '5 gp',
        'damage': '1d6 bludgeoning',
        'weight': '4 lb',
        'properties': [],
    },
    'quarterstaff': {
        'name': 'Quarterstaff',
        'type': 'Simple Melee',
        'cost': '2 sp',
        'damage': '1d6 bludgeoning',
        'weight': '4 lb',
        'properties': ['Versatile (1d8)'],
    },
    'spear': {
        'name': 'Spear',
        'type': 'Simple Melee',
        'cost': '1 gp',
        'damage': '1d6 piercing',
        'weight': '3 lb',
        'properties': ['Thrown (20/60)', 'Versatile (1d8)'],
    },
    # === WEAPONS - Simple Ranged ===
    'light_crossbow': {
        'name': 'Light Crossbow',
        'type': 'Simple Ranged',
        'cost': '25 gp',
        'damage': '1d8 piercing',
        'weight': '5 lb',
        'properties': ['Ammunition (80/320)', 'Loading', 'Two-handed'],
    },
    'shortbow': {
        'name': 'Shortbow',
        'type': 'Simple Ranged',
        'cost': '25 gp',
        'damage': '1d6 piercing',
        'weight': '2 lb',
        'properties': ['Ammunition (80/320)', 'Two-handed'],
    },
    # === WEAPONS - Martial Melee ===
    'battleaxe': {
        'name': 'Battleaxe',
        'type': 'Martial Melee',
        'cost': '10 gp',
        'damage': '1d8 slashing',
        'weight': '4 lb',
        'properties': ['Versatile (1d10)'],
    },
    'greatsword': {
        'name': 'Greatsword',
        'type': 'Martial Melee',
        'cost': '50 gp',
        'damage': '2d6 slashing',
        'weight': '6 lb',
        'properties': ['Heavy', 'Two-handed'],
    },
    'longsword': {
        'name': 'Longsword',
        'type': 'Martial Melee',
        'cost': '15 gp',
        'damage': '1d8 slashing',
        'weight': '3 lb',
        'properties': ['Versatile (1d10)'],
    },
    'rapier': {
        'name': 'Rapier',
        'type': 'Martial Melee',
        'cost': '25 gp',
        'damage': '1d8 piercing',
        'weight': '2 lb',
        'properties': ['Finesse'],
    },
    'scimitar': {
        'name': 'Scimitar',
        'type': 'Martial Melee',
        'cost': '25 gp',
        'damage': '1d6 slashing',
        'weight': '3 lb',
        'properties': ['Finesse', 'Light'],
    },
    'shortsword': {
        'name': 'Shortsword',
        'type': 'Martial Melee',
        'cost': '10 gp',
        'damage': '1d6 piercing',
        'weight': '2 lb',
        'properties': ['Finesse', 'Light'],
    },
    'warhammer': {
        'name': 'Warhammer',
        'type': 'Martial Melee',
        'cost': '15 gp',
        'damage': '1d8 bludgeoning',
        'weight': '2 lb',
        'properties': ['Versatile (1d10)'],
    },
    # === WEAPONS - Martial Ranged ===
    'hand_crossbow': {
        'name': 'Hand Crossbow',
        'type': 'Martial Ranged',
        'cost': '75 gp',
        'damage': '1d6 piercing',
        'weight': '3 lb',
        'properties': ['Ammunition (30/120)', 'Light', 'Loading'],
    },
    'heavy_crossbow': {
        'name': 'Heavy Crossbow',
        'type': 'Martial Ranged',
        'cost': '50 gp',
        'damage': '1d10 piercing',
        'weight': '18 lb',
        'properties': ['Ammunition (100/400)', 'Heavy', 'Loading', 'Two-handed'],
    },
    'longbow': {
        'name': 'Longbow',
        'type': 'Martial Ranged',
        'cost': '50 gp',
        'damage': '1d8 piercing',
        'weight': '2 lb',
        'properties': ['Ammunition (150/600)', 'Heavy', 'Two-handed'],
    },
    # === ARMOR ===
    'padded_armor': {
        'name': 'Padded Armor',
        'type': 'Light Armor',
        'cost': '5 gp',
        'ac': '11 + DEX',
        'weight': '8 lb',
        'properties': ['Stealth disadvantage'],
    },
    'leather_armor': {
        'name': 'Leather Armor',
        'type': 'Light Armor',
        'cost': '10 gp',
        'ac': '11 + DEX',
        'weight': '10 lb',
        'properties': [],
    },
    'studded_leather': {
        'name': 'Studded Leather',
        'type': 'Light Armor',
        'cost': '45 gp',
        'ac': '12 + DEX',
        'weight': '13 lb',
        'properties': [],
    },
    'hide_armor': {
        'name': 'Hide Armor',
        'type': 'Medium Armor',
        'cost': '10 gp',
        'ac': '12 + DEX (max 2)',
        'weight': '12 lb',
        'properties': [],
    },
    'chain_shirt': {
        'name': 'Chain Shirt',
        'type': 'Medium Armor',
        'cost': '50 gp',
        'ac': '13 + DEX (max 2)',
        'weight': '20 lb',
        'properties': [],
    },
    'scale_mail': {
        'name': 'Scale Mail',
        'type': 'Medium Armor',
        'cost': '50 gp',
        'ac': '14 + DEX (max 2)',
        'weight': '45 lb',
        'properties': ['Stealth disadvantage'],
    },
    'breastplate': {
        'name': 'Breastplate',
        'type': 'Medium Armor',
        'cost': '400 gp',
        'ac': '14 + DEX (max 2)',
        'weight': '20 lb',
        'properties': [],
    },
    'half_plate': {
        'name': 'Half Plate',
        'type': 'Medium Armor',
        'cost': '750 gp',
        'ac': '15 + DEX (max 2)',
        'weight': '40 lb',
        'properties': ['Stealth disadvantage'],
    },
    'ring_mail': {
        'name': 'Ring Mail',
        'type': 'Heavy Armor',
        'cost': '30 gp',
        'ac': '14',
        'weight': '40 lb',
        'properties': ['Stealth disadvantage'],
    },
    'chain_mail': {
        'name': 'Chain Mail',
        'type': 'Heavy Armor',
        'cost': '75 gp',
        'ac': '16',
        'weight': '55 lb',
        'properties': ['STR 13 required', 'Stealth disadvantage'],
    },
    'splint_armor': {
        'name': 'Splint Armor',
        'type': 'Heavy Armor',
        'cost': '200 gp',
        'ac': '17',
        'weight': '60 lb',
        'properties': ['STR 15 required', 'Stealth disadvantage'],
    },
    'plate_armor': {
        'name': 'Plate Armor',
        'type': 'Heavy Armor',
        'cost': '1500 gp',
        'ac': '18',
        'weight': '65 lb',
        'properties': ['STR 15 required', 'Stealth disadvantage'],
    },
    'shield': {
        'name': 'Shield',
        'type': 'Shield',
        'cost': '10 gp',
        'ac': '+2',
        'weight': '6 lb',
        'properties': [],
    },
    # === ADVENTURING GEAR ===
    'backpack': {
        'name': 'Backpack',
        'type': 'Adventuring Gear',
        'cost': '2 gp',
        'weight': '5 lb',
        'description': 'Holds up to 30 pounds or 1 cubic foot of gear.',
    },
    'bedroll': {
        'name': 'Bedroll',
        'type': 'Adventuring Gear',
        'cost': '1 gp',
        'weight': '7 lb',
        'description': 'Sleeping bag for rest in the wilderness.',
    },
    'crowbar': {
        'name': 'Crowbar',
        'type': 'Adventuring Gear',
        'cost': '2 gp',
        'weight': '5 lb',
        'description': 'Advantage on STR checks where leverage can be applied.',
    },
    'grappling_hook': {
        'name': 'Grappling Hook',
        'type': 'Adventuring Gear',
        'cost': '2 gp',
        'weight': '4 lb',
        'description': 'Attach to rope for climbing.',
    },
    'lantern_hooded': {
        'name': 'Lantern, Hooded',
        'type': 'Adventuring Gear',
        'cost': '5 gp',
        'weight': '2 lb',
        'description': 'Casts bright light 30 ft, dim light 30 ft more. Burns 6 hours on 1 pint oil.',
    },
    'rations': {
        'name': 'Rations (1 day)',
        'type': 'Adventuring Gear',
        'cost': '5 sp',
        'weight': '2 lb',
        'description': 'Dry foods suitable for extended travel.',
    },
    'rope_50': {
        'name': 'Rope, Hempen (50 ft)',
        'type': 'Adventuring Gear',
        'cost': '1 gp',
        'weight': '10 lb',
        'description': 'Has 2 HP, can be burst with DC 17 Strength check.',
    },
    'rope_silk': {
        'name': 'Rope, Silk (50 ft)',
        'type': 'Adventuring Gear',
        'cost': '10 gp',
        'weight': '5 lb',
        'description': 'Has 2 HP, can be burst with DC 17 Strength check.',
    },
    'thieves_tools': {
        'name': "Thieves' Tools",
        'type': 'Adventuring Gear',
        'cost': '25 gp',
        'weight': '1 lb',
        'description': 'Pick locks and disarm traps. Proficiency required.',
    },
    'torch': {
        'name': 'Torch',
        'type': 'Adventuring Gear',
        'cost': '1 cp',
        'weight': '1 lb',
        'description': 'Bright light 20 ft, dim light 20 ft more. Burns for 1 hour.',
    },
    'waterskin': {
        'name': 'Waterskin',
        'type': 'Adventuring Gear',
        'cost': '2 sp',
        'weight': '5 lb (full)',
        'description': 'Holds 4 pints of liquid.',
    },
    # === POTIONS & MAGIC ITEMS ===
    'healing_potion': {
        'name': 'Potion of Healing',
        'type': 'Potion',
        'cost': '50 gp',
        'rarity': 'Common',
        'description': 'Regain 2d4+2 hit points when you drink this potion.',
    },
    'greater_healing_potion': {
        'name': 'Potion of Greater Healing',
        'type': 'Potion',
        'cost': '150 gp',
        'rarity': 'Uncommon',
        'description': 'Regain 4d4+4 hit points when you drink this potion.',
    },
    'superior_healing_potion': {
        'name': 'Potion of Superior Healing',
        'type': 'Potion',
        'cost': '450 gp',
        'rarity': 'Rare',
        'description': 'Regain 8d4+8 hit points when you drink this potion.',
    },
    'bag_of_holding': {
        'name': 'Bag of Holding',
        'type': 'Wondrous Item',
        'rarity': 'Uncommon',
        'description': 'Interior is 64 cubic feet. Holds up to 500 pounds but always weighs 15 pounds. Retrieving an item requires an action.',
    },
    'cloak_of_protection': {
        'name': 'Cloak of Protection',
        'type': 'Wondrous Item',
        'rarity': 'Uncommon',
        'attunement': True,
        'description': 'You gain a +1 bonus to AC and saving throws while you wear this cloak.',
    },
    'ring_of_protection': {
        'name': 'Ring of Protection',
        'type': 'Ring',
        'rarity': 'Rare',
        'attunement': True,
        'description': 'You gain a +1 bonus to AC and saving throws while wearing this ring.',
    },
    'weapon_plus_1': {
        'name': 'Weapon +1',
        'type': 'Weapon (any)',
        'rarity': 'Uncommon',
        'description': 'You have a +1 bonus to attack and damage rolls made with this magic weapon.',
    },
    'armor_plus_1': {
        'name': 'Armor +1',
        'type': 'Armor (any)',
        'rarity': 'Rare',
        'description': 'You have a +1 bonus to AC while wearing this armor.',
    },
}

# ============================================================
# Shadowdark Items
# ============================================================

SHADOWDARK_ITEMS = {
    # === WEAPONS ===
    'bastard_sword': {
        'name': 'Bastard Sword',
        'type': 'Weapon',
        'cost': '20 gp',
        'damage': '1d8/1d10 (2H)',
        'properties': ['Versatile'],
        'description': 'A versatile sword that can be wielded one or two-handed.',
    },
    'crossbow': {
        'name': 'Crossbow',
        'type': 'Weapon',
        'cost': '8 gp',
        'damage': '1d6',
        'properties': ['Ranged', 'Loading'],
        'description': 'Requires one action to reload after each shot.',
    },
    'dagger_sd': {
        'name': 'Dagger',
        'type': 'Weapon',
        'cost': '1 gp',
        'damage': '1d4',
        'properties': ['Finesse', 'Thrown'],
        'description': 'Can use DEX for attack and damage. Throwable.',
    },
    'greataxe_sd': {
        'name': 'Greataxe',
        'type': 'Weapon',
        'cost': '10 gp',
        'damage': '1d10',
        'properties': ['Two-handed'],
        'description': 'A massive two-handed axe.',
    },
    'longbow_sd': {
        'name': 'Longbow',
        'type': 'Weapon',
        'cost': '8 gp',
        'damage': '1d8',
        'properties': ['Ranged', 'Two-handed'],
        'description': 'A powerful ranged weapon.',
    },
    'longsword_sd': {
        'name': 'Longsword',
        'type': 'Weapon',
        'cost': '9 gp',
        'damage': '1d8',
        'properties': [],
        'description': 'A standard one-handed sword.',
    },
    'mace_sd': {
        'name': 'Mace',
        'type': 'Weapon',
        'cost': '5 gp',
        'damage': '1d6',
        'properties': [],
        'description': 'A blunt weapon favored by priests.',
    },
    'shortbow_sd': {
        'name': 'Shortbow',
        'type': 'Weapon',
        'cost': '6 gp',
        'damage': '1d4',
        'properties': ['Ranged', 'Two-handed'],
        'description': 'A compact bow for quick shots.',
    },
    'shortsword_sd': {
        'name': 'Shortsword',
        'type': 'Weapon',
        'cost': '7 gp',
        'damage': '1d6',
        'properties': ['Finesse'],
        'description': 'A light blade that can use DEX.',
    },
    'spear_sd': {
        'name': 'Spear',
        'type': 'Weapon',
        'cost': '1 gp',
        'damage': '1d6',
        'properties': ['Thrown', 'Versatile (1d8)'],
        'description': 'Can be thrown or used two-handed.',
    },
    'staff_sd': {
        'name': 'Staff',
        'type': 'Weapon',
        'cost': '1 gp',
        'damage': '1d4',
        'properties': ['Two-handed'],
        'description': 'A simple wooden staff, favored by wizards.',
    },
    'warhammer_sd': {
        'name': 'Warhammer',
        'type': 'Weapon',
        'cost': '10 gp',
        'damage': '1d10',
        'properties': ['Two-handed'],
        'description': 'A devastating two-handed hammer.',
    },
    # === ARMOR ===
    'leather_sd': {
        'name': 'Leather Armor',
        'type': 'Armor',
        'cost': '10 gp',
        'ac': '11 + DEX',
        'properties': [],
        'description': 'Light armor that allows full DEX bonus.',
    },
    'chainmail_sd': {
        'name': 'Chainmail',
        'type': 'Armor',
        'cost': '60 gp',
        'ac': '15',
        'properties': ['Noisy'],
        'description': 'Heavy armor. Disadvantage on stealth.',
    },
    'plate_sd': {
        'name': 'Plate Armor',
        'type': 'Armor',
        'cost': '130 gp',
        'ac': '17',
        'properties': ['Noisy'],
        'description': 'The best protection available. Disadvantage on stealth.',
    },
    'shield_sd': {
        'name': 'Shield',
        'type': 'Shield',
        'cost': '5 gp',
        'ac': '+2',
        'properties': [],
        'description': 'Adds +2 to AC when wielded.',
    },
    # === GEAR ===
    'torch_sd': {
        'name': 'Torch',
        'type': 'Gear',
        'cost': '5 cp',
        'slots': '1',
        'description': 'Burns for 1 hour. Near radius light.',
    },
    'lantern_sd': {
        'name': 'Lantern',
        'type': 'Gear',
        'cost': '5 gp',
        'slots': '1',
        'description': 'Burns 4 hours per flask of oil. Near radius light.',
    },
    'oil_flask': {
        'name': 'Oil Flask',
        'type': 'Gear',
        'cost': '5 sp',
        'slots': '1',
        'description': 'Fuel for lantern. Can be thrown as improvised weapon.',
    },
    'rope_60_sd': {
        'name': 'Rope (60 ft)',
        'type': 'Gear',
        'cost': '1 gp',
        'slots': '1',
        'description': 'Standard adventuring rope.',
    },
    'grappling_hook_sd': {
        'name': 'Grappling Hook',
        'type': 'Gear',
        'cost': '1 gp',
        'slots': '1',
        'description': 'Attach to rope for climbing.',
    },
    'rations_sd': {
        'name': 'Rations (3 days)',
        'type': 'Gear',
        'cost': '3 gp',
        'slots': '1',
        'description': 'Food for 3 days of travel.',
    },
    'thieves_tools_sd': {
        'name': "Thieves' Tools",
        'type': 'Gear',
        'cost': '25 gp',
        'slots': '1',
        'description': 'Required for picking locks and disarming traps.',
    },
    'holy_symbol': {
        'name': 'Holy Symbol',
        'type': 'Gear',
        'cost': '25 gp',
        'slots': '1',
        'description': 'Required focus for priest spells.',
    },
    'spellbook': {
        'name': 'Spellbook',
        'type': 'Gear',
        'cost': '50 gp',
        'slots': '1',
        'description': 'Required for wizard to prepare spells.',
    },
    # === MAGIC ITEMS ===
    'potion_healing_sd': {
        'name': 'Potion of Healing',
        'type': 'Potion',
        'rarity': 'Common',
        'description': 'Heals 1d8 HP. One use.',
    },
    'scroll_spell_1': {
        'name': 'Spell Scroll (Tier 1)',
        'type': 'Scroll',
        'rarity': 'Common',
        'description': 'Contains one tier 1 spell. Consumed on use.',
    },
    'magic_sword': {
        'name': '+1 Magic Sword',
        'type': 'Magic Weapon',
        'rarity': 'Uncommon',
        'description': '+1 to attack and damage rolls.',
    },
    'magic_armor': {
        'name': '+1 Magic Armor',
        'type': 'Magic Armor',
        'rarity': 'Uncommon',
        'description': '+1 to AC beyond base armor.',
    },
}


# ============================================================
# Shadowdark SRD Data
# ============================================================

SHADOWDARK_ANCESTRIES = {
    'human': {
        'name': 'Human',
        'traits': [
            'Ambitious: You gain 1 additional talent roll at 1st level.',
        ],
    },
    'elf': {
        'name': 'Elf',
        'traits': [
            'Farsight: You get a +1 bonus to attack rolls with ranged weapons or a +1 bonus to spellcasting checks.',
        ],
    },
    'dwarf': {
        'name': 'Dwarf',
        'traits': [
            'Stout: You have advantage on CON checks vs poison. You can see in darkness up to near range.',
        ],
    },
    'halfling': {
        'name': 'Halfling',
        'traits': [
            'Stealthy: Once per day, you can become invisible for 3 rounds.',
        ],
    },
    'goblin': {
        'name': 'Goblin',
        'traits': [
            'Keen Senses: You can see in darkness up to far range.',
        ],
    },
    'half_orc': {
        'name': 'Half-Orc',
        'traits': [
            'Mighty: You have +1 to all melee damage rolls.',
        ],
    },
}

SHADOWDARK_CLASSES = {
    'fighter': {
        'name': 'Fighter',
        'weapons': 'All weapons and shields',
        'armor': 'All armor and shields',
        'hit_die': 'd8',
        'features': [
            'Grit: Choose STR or DEX. You have advantage on checks with that stat.',
            'Hauler: You gain +2 gear slots.',
            'Weapon Mastery: +1 to attack and damage with one weapon type.',
        ],
    },
    'thief': {
        'name': 'Thief',
        'weapons': 'Crossbows, daggers, clubs, shortbows, shortswords',
        'armor': 'Leather armor, mithral chainmail',
        'hit_die': 'd4',
        'features': [
            'Backstab: +1 die of damage when attacking from surprise.',
            'Thievery: Advantage on DEX checks for thief skills.',
        ],
    },
    'priest': {
        'name': 'Priest',
        'weapons': 'Clubs, crossbows, daggers, maces, longswords, staffs, warhammers',
        'armor': 'All armor and shields',
        'hit_die': 'd6',
        'features': [
            'Spellcasting: Cast priest spells using WIS.',
            'Turn Undead: Make spellcasting check to turn undead.',
        ],
    },
    'wizard': {
        'name': 'Wizard',
        'weapons': 'Daggers, staffs',
        'armor': 'None',
        'hit_die': 'd4',
        'features': [
            'Spellcasting: Cast wizard spells using INT.',
            'Learning Spells: Learn 3 spells at 1st level, +1 per level.',
        ],
    },
}


# ============================================================
# Open5e API Integration
# ============================================================

class Open5eAPI:
    """Fetch additional content from Open5e API."""
    
    BASE_URL = "https://api.open5e.com/v1"
    
    @staticmethod
    def _ensure_cache_dir():
        """Ensure cache directory exists."""
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    @staticmethod
    def _get_cache_path(category: str, key: str) -> str:
        """Get cache file path."""
        return os.path.join(CACHE_DIR, f"{category}_{key}.json")
    
    @staticmethod
    def _load_from_cache(category: str, key: str) -> Optional[dict]:
        """Load data from cache if available."""
        path = Open5eAPI._get_cache_path(category, key)
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    @staticmethod
    def _save_to_cache(category: str, key: str, data: dict):
        """Save data to cache."""
        Open5eAPI._ensure_cache_dir()
        path = Open5eAPI._get_cache_path(category, key)
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    @staticmethod
    def search_spells(query: str) -> List[dict]:
        """Search for spells by name."""
        # Check cache first
        cached = Open5eAPI._load_from_cache('spell_search', query.lower())
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{Open5eAPI.BASE_URL}/spells/",
                params={'search': query, 'limit': 20},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                Open5eAPI._save_to_cache('spell_search', query.lower(), results)
                return results
        except Exception:
            pass
        return []
    
    @staticmethod
    def get_spell(slug: str) -> Optional[dict]:
        """Get spell details by slug."""
        cached = Open5eAPI._load_from_cache('spell', slug)
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{Open5eAPI.BASE_URL}/spells/{slug}/",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                Open5eAPI._save_to_cache('spell', slug, data)
                return data
        except Exception:
            pass
        return None
    
    @staticmethod
    def search_monsters(query: str) -> List[dict]:
        """Search for monsters by name."""
        cached = Open5eAPI._load_from_cache('monster_search', query.lower())
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{Open5eAPI.BASE_URL}/monsters/",
                params={'search': query, 'limit': 20},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                Open5eAPI._save_to_cache('monster_search', query.lower(), results)
                return results
        except Exception:
            pass
        return []
    
    @staticmethod
    def get_monster(slug: str) -> Optional[dict]:
        """Get monster details by slug."""
        cached = Open5eAPI._load_from_cache('monster', slug)
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{Open5eAPI.BASE_URL}/monsters/{slug}/",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                Open5eAPI._save_to_cache('monster', slug, data)
                return data
        except Exception:
            pass
        return None
    
    @staticmethod
    def search_items(query: str) -> List[dict]:
        """Search for magic items."""
        cached = Open5eAPI._load_from_cache('item_search', query.lower())
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{Open5eAPI.BASE_URL}/magicitems/",
                params={'search': query, 'limit': 20},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                Open5eAPI._save_to_cache('item_search', query.lower(), results)
                return results
        except Exception:
            pass
        return []


# ============================================================
# Reference Helper Functions
# ============================================================

def get_all_srd_spells() -> Dict[str, dict]:
    """Get all SRD spells."""
    return DND5E_SPELLS

def get_spell(spell_id: str) -> Optional[dict]:
    """Get spell by ID from SRD or cache."""
    if spell_id in DND5E_SPELLS:
        return DND5E_SPELLS[spell_id]
    return Open5eAPI._load_from_cache('spell', spell_id)

def get_all_srd_races() -> Dict[str, dict]:
    """Get all SRD races."""
    return DND5E_RACES

def get_all_conditions() -> Dict[str, dict]:
    """Get all conditions."""
    return DND5E_CONDITIONS

def get_all_srd_items() -> Dict[str, dict]:
    """Get all SRD items."""
    return DND5E_ITEMS

def get_shadowdark_ancestries() -> Dict[str, dict]:
    """Get Shadowdark ancestries."""
    return SHADOWDARK_ANCESTRIES

def get_shadowdark_classes() -> Dict[str, dict]:
    """Get Shadowdark classes."""
    return SHADOWDARK_CLASSES

def get_shadowdark_items() -> Dict[str, dict]:
    """Get Shadowdark items."""
    return SHADOWDARK_ITEMS


# ============================================================
# EXTENSIBLE GAME SYSTEM REGISTRATION
# ============================================================
# 
# To add a new game system:
# 
# 1. Add your data dictionaries at the top of this file:
#    MYGAME_CLASSES = { ... }
#    MYGAME_ITEMS = { ... }
# 
# 2. Register the system in GAME_SYSTEMS below
# 
# 3. Add getter functions:
#    def get_mygame_classes() -> Dict[str, dict]:
#        return MYGAME_CLASSES
# 
# 4. Update ttrpg.py to include your system in:
#    - SYSTEMS list
#    - SYSTEM_INFO dict
#    - ref_categories dict
#    - _load_reference_category() function
# 
# Data structure conventions:
# - 'name': Display name (required)
# - 'description': Long text description
# - 'traits' / 'features' / 'effects': List of strings
# - 'properties': List of tags/keywords
# - Include game-specific fields as needed
#

GAME_SYSTEMS = {
    'dnd5e': {
        'name': 'D&D 5th Edition',
        'version': 'SRD 5.1',
        'categories': {
            'spells': get_all_srd_spells,
            'races': get_all_srd_races,
            'conditions': get_all_conditions,
            'items': get_all_srd_items,
        },
        'online_api': Open5eAPI,
    },
    'shadowdark': {
        'name': 'Shadowdark RPG',
        'version': 'Core Rules',
        'categories': {
            'ancestries': get_shadowdark_ancestries,
            'classes': get_shadowdark_classes,
            'items': get_shadowdark_items,
        },
        'online_api': None,
    },
    # === ADD NEW SYSTEMS HERE ===
    # 'pathfinder2e': {
    #     'name': 'Pathfinder 2e',
    #     'version': 'Core Rulebook',
    #     'categories': {
    #         'ancestries': get_pf2e_ancestries,
    #         'classes': get_pf2e_classes,
    #         'spells': get_pf2e_spells,
    #         'items': get_pf2e_items,
    #     },
    #     'online_api': None,  # Or custom API class
    # },
}

def get_registered_systems() -> Dict[str, dict]:
    """Get all registered game systems."""
    return GAME_SYSTEMS

def get_system_data(system_id: str, category: str) -> Dict[str, dict]:
    """Get data for a specific system and category."""
    system = GAME_SYSTEMS.get(system_id)
    if not system:
        return {}
    
    getter = system.get('categories', {}).get(category)
    if callable(getter):
        return getter()
    return {}

