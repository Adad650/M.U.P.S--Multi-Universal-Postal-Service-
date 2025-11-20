# Multi-Universal Postal Service (M.U.P.S)

A 2D platformer where you play as an interdimensional postman delivering packages across procedurally generated dimensions, each with unique physics and challenges.

## 🎮 Gameplay

### Controls
- `Space` - Jump
- `A` - Move Left
- `D` - Move Right
- `E` - Interact with office elements (Shop and computer)
- `Escape` - Exit interactive menus (Shop and computer)

### Objective
Navigate through various dimensions, each with unique properties, to deliver packages while overcoming platforming challenges and hazards.

## 🌌 Features

### Procedural Generation
- Infinite replayability with uniquely generated dimensions
- Each dimension has its own seed for consistent regeneration
- Dynamic platform generation based on dimension properties
- Smart generation ensures all levels are solvable

### Dimension Properties
- Variable gravity
- Unique platform layouts
- Different visual themes
- Special hazards and challenges
- Custom physics for each dimension

### Dimension Lore & Backgrounds
- Contracts are bound to bespoke dimension archetypes with unique skies and parallax details
- Gradient horizons, themed hazards, and lore snippets set the mood for every run
- Ambient cues on the HUD remind you what kind of dimension you are traversing

### Hub Crew & Dialogues
- Dispatcher Rae and Archivist Zell now inhabit the office with contextual dialogue
- Chat with the crew for tips about streaks, ranks, upcoming contracts, and lore
- Conversations can be advanced or skipped at any time for smooth pacing

### Postal Reputation System
- Completing deliveries raises your interdimensional reputation and unlocks postal ranks
- Milestones grant permanent perks: payout multipliers, extra lives, cash bonuses, and suit tints
- On-screen toasts, win panels, and HUD widgets track streaks, ranks, and upcoming rewards

### Courier Codex
- A dedicated log terminal catalogs every dimension blueprint you discover
- View lore blurbs, hazard notes, completion counts, and personal best times from the hub computer (`C`)
- Gives players a long-term objective to fully scan the multiverse

### Data Beacon Hunts
- Each generated level hides shimmering beacons perched on distant pads
- Collect beacons for bonus credits, XP, and codex accolades; HUD tracks progress live
- Optional challenges encourage revisiting runs for 100% completion

### Shop System
- Purchase upgrades and cosmetics
- Unlock new abilities
- Customize your postman
- Earn currency by completing deliveries

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- Pygame library

### Installation
1. Clone the repository:
   ```bash
   git clone https://https://github.com/Adad650/M.U.P.S--Multi-Universal-Postal-Service-
   cd mups-game
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the game:
   ```bash
   python3 main.py
   ```

## 🛠 Development

### Project Structure
- `main.py` - Main game loop and initialization
- `player.py` - Player character and controls
- `worldGen.py` - Procedural world generation
- `gravity.py` - Physics and movement systems
- `assets/` - Game assets (sprites, sounds, etc.)

### Contributing
1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments
- Built with Python and Pygame
- Inspired by classic platformers and roguelikes
