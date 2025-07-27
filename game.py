
import sys
import secrets
import hmac
import hashlib
from tabulate import tabulate

# ==============================================================================
# 1. Error Handling Class (UPDATED)
# ==============================================================================

class ValidationError(Exception):
    """
    Custom exception for argument validation errors.
    Provides a formatted message including an example of correct usage.
    """
    _invocation_command = "python"

    @staticmethod
    def set_invocation_command(command: str):
        """Sets the command used to run the script (e.g., 'python' or 'py')."""
        ValidationError._invocation_command = command

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        script_name = sys.argv[0] if sys.argv else 'game.py'
        example = (
            f"{ValidationError._invocation_command} {script_name} "
            f"2,2,4,4,9,9 1,1,6,6,8,8 3,3,5,5,7,7"
        )
        return f"\nArgument Error: {self.message}\n\nExample usage:\n{example}\n"

ValidationError.NOT_ENOUGH_DICE = ValidationError("Please specify at least three dice.")
ValidationError.INCONSISTENT_FACES = ValidationError("All dice must have the same number of faces.")
ValidationError.NON_INTEGER_VALUE = ValidationError("All dice faces must be integer values.")

# ==============================================================================
# 2. Data Structure for a Die
# ==============================================================================

class Die:
    def __init__(self, faces: list[int]):
        if not faces:
            raise ValueError("A die must have at least one face.")
        self.faces = faces

    def __str__(self) -> str:
        return ",".join(map(str, self.faces))

    def __len__(self) -> int:
        return len(self.faces)

# ==============================================================================
# 3. Command-Line Argument Parser
# ==============================================================================

class DiceParser:
    @staticmethod
    def parse(args: list[str]) -> list[Die]:
        if len(args) < 3:
            raise ValidationError.NOT_ENOUGH_DICE
        try:
            dice_list = [Die([int(f) for f in arg.split(',') if f]) for arg in args]
        except ValueError:
            raise ValidationError.NON_INTEGER_VALUE
        if not all(len(d) == len(dice_list[0]) for d in dice_list):
            raise ValidationError.INCONSISTENT_FACES
        return dice_list

# ==============================================================================
# 4. Cryptographic Operations Provider
# ==============================================================================

class CryptoProvider:
    @staticmethod
    def generate_key() -> bytes:
        return secrets.token_bytes(32)

    @staticmethod
    def generate_secure_random(max_val: int) -> int:
        return secrets.randbelow(max_val)

    @staticmethod
    def calculate_hmac(key: bytes, message_int: int) -> str:
        message_bytes = str(message_int).encode('utf-8')
        h = hmac.new(key, message_bytes, hashlib.sha3_256)
        return h.hexdigest().upper()

# ==============================================================================
# 5. Probability Calculation Logic
# ==============================================================================

class ProbabilityCalculator:
    @staticmethod
    def calculate_win_probability(die1: Die, die2: Die) -> float:
        wins = sum(1 for f1 in die1.faces for f2 in die2.faces if f1 > f2)
        total_outcomes = len(die1) * len(die2)
        return wins / total_outcomes if total_outcomes > 0 else 0.0

# ==============================================================================
# 6. Help Table Generation
# ==============================================================================

class HelpTableGenerator:
    @staticmethod
    def generate_table(all_dice: list[Die], calculator: ProbabilityCalculator) -> str:
        headers = ["User v PC >"] + [str(d) for d in all_dice]
        table_data = []
        for user_die in all_dice:
            row = [str(user_die)]
            for pc_die in all_dice:
                prob = calculator.calculate_win_probability(user_die, pc_die)
                cell = f"*{prob:.4f}*" if user_die is pc_die else f"{prob:.4f}"
                row.append(cell)
            table_data.append(row)
        
        intro = (
            "\n--- Win Probability Table ---\n"
            "This table shows the probability of the User's die (rows) winning against the PC's die (columns).\n"
            "* Diagonal values show probability of a die winning against an identical one.\n"
        )
        return intro + tabulate(table_data, headers=headers, tablefmt="grid")

# ==============================================================================
# 7. Console User Interface
# ==============================================================================

class GameUI:
    def display_message(self, text: str):
        print(text)

    def display_hmac(self, hmac_hex: str):
        print(f"HMAC: {hmac_hex}")

    def display_key_and_move(self, key: bytes, move: int, name: str = "My choice"):
        print(f"{name}: {move} (Secret Key: {key.hex().upper()})")

    def get_user_choice(self, prompt: str, options: list[str], allow_help: bool = True) -> str:
        while True:
            print(f"\n{prompt}")
            for i, option in enumerate(options):
                print(f" {i} - {option}")
            
            print("\n X - Exit")
            if allow_help:
                print(" ? - Help")

            choice = input("Your choice: ").strip().lower()

            if choice == 'x':
                print("Exiting game. Goodbye!")
                sys.exit(0)
            if choice == '?' and allow_help:
                return '?'
            
            if choice.isdigit():
                choice_int = int(choice)
                if 0 <= choice_int < len(options):
                    return str(choice_int)
            
            print("Invalid choice. Please enter a valid number, '?', or 'X'.")

# ==============================================================================
# 8. Provably Fair Random Number Generation & Game Logic
# ==============================================================================

class FairInteraction:
    def __init__(self, crypto_provider: CryptoProvider, ui: GameUI):
        self.crypto = crypto_provider
        self.ui = ui

    def determine_first_player(self) -> bool:
        self.ui.display_message("\nLet's determine who makes the first move.")
        computer_bit = self.crypto.generate_secure_random(2)
        key = self.crypto.generate_key()
        hmac_val = self.crypto.calculate_hmac(key, computer_bit)
        self.ui.display_message(f"I have chosen a random value in range 0..1 (HMAC={hmac_val}).")
        
        options = ["0", "1"]
        user_bit_str = self.ui.get_user_choice("Try to guess my choice.", options, allow_help=False)
        user_bit = int(user_bit_str)
        
        self.ui.display_key_and_move(key, computer_bit)
        user_goes_first = (user_bit == computer_bit)
        return user_goes_first

    def get_fair_roll_index(self, max_val: int, prompt: str) -> int:
        self.ui.display_message(f"I have chosen a random value in range 0..{max_val-1}.")
        computer_move = self.crypto.generate_secure_random(max_val)
        key = self.crypto.generate_key()
        hmac_val = self.crypto.calculate_hmac(key, computer_move)
        self.ui.display_hmac(hmac_val)

        options = [str(i) for i in range(max_val)]
        user_move_str = self.ui.get_user_choice(prompt, options, allow_help=False)
        user_move = int(user_move_str)
        
        result = (computer_move + user_move) % max_val
        
        self.ui.display_key_and_move(key, computer_move, name="My number")
        self.ui.display_message(f"Fair random number result: ({computer_move} + {user_move}) mod {max_val} = {result}")
        return result

# ==============================================================================
# 9. Main Game Controller
# ==============================================================================

class GameController:
    def __init__(self, dice: list[Die], ui: GameUI, interaction: FairInteraction, help_gen: HelpTableGenerator):
        self.all_dice = dice
        self.ui = ui
        self.interaction = interaction
        self.help_gen = help_gen

    def run(self):
        self.ui.display_message("--- Welcome to the Non-Transitive Dice Game! ---")
        while True:
            self._play_round()
            play_again = input("\nPlay another round? (y/n): ").strip().lower()
            if play_again != 'y':
                self.ui.display_message("Thanks for playing!")
                break

    def _play_round(self):
        user_goes_first = self.interaction.determine_first_player()
        
        player_die, computer_die = self._select_dice(user_goes_first)
        
        self.ui.display_message(f"\nYour die: [{player_die}]")
        self.ui.display_message(f"My die:   [{computer_die}]")

        num_faces = len(player_die)
        self.ui.display_message("\n--- Time to roll! ---")
        
        self.ui.display_message("\nIt is my time to roll.")
        computer_roll_index = self.interaction.get_fair_roll_index(
            num_faces, f"Add your number modulo {num_faces}."
        )
        computer_roll_value = computer_die.faces[computer_roll_index]
        self.ui.display_message(f"Result of my roll is {computer_roll_value}.")

        self.ui.display_message("\nIt is your time to roll.")
        player_roll_index = self.interaction.get_fair_roll_index(
            num_faces, f"Add your number modulo {num_faces}."
        )
        player_roll_value = player_die.faces[player_roll_index]
        self.ui.display_message(f"Result of your roll is {player_roll_value}.")
        
        self.ui.display_message("\n--- Results ---")
        self.ui.display_message(f"You rolled {player_roll_value}, I rolled {computer_roll_value}.")
        if player_roll_value > computer_roll_value:
            self.ui.display_message(f"You won! ({player_roll_value} > {computer_roll_value})")
        elif computer_roll_value > player_roll_value:
            self.ui.display_message(f"I won! ({computer_roll_value} > {player_roll_value})")
        else:
            self.ui.display_message("It's a draw!")
    
    def _select_dice(self, user_goes_first: bool):
        available_dice = list(self.all_dice)
        if user_goes_first:
            self.ui.display_message("You make the first move and choose the dice.")
            player_die = self._get_player_die_choice(available_dice)
            available_dice.remove(player_die)
            computer_die = secrets.choice(available_dice)
        else:
            self.ui.display_message("I make the first move and choose the dice.")
            computer_die = secrets.choice(available_dice)
            available_dice.remove(computer_die)
            self.ui.display_message(f"I choose dice [{computer_die}].")
            player_die = self._get_player_die_choice(available_dice)
        return player_die, computer_die
    
    def _get_player_die_choice(self, available_dice: list[Die]):
        while True:
            options = [str(d) for d in available_dice]
            choice_str = self.ui.get_user_choice("Select your dice:", options, allow_help=True)
            if choice_str == '?':
                table = self.help_gen.generate_table(self.all_dice, ProbabilityCalculator)
                self.ui.display_message(table)
                continue
            return available_dice[int(choice_str)]

# ==============================================================================
# 10. Main Execution Block (UPDATED)
# ==============================================================================

def main():
    try:
        # Dynamically determine the command used to invoke the script
        if 'py.exe' in sys.executable.lower():
            ValidationError.set_invocation_command('py')
        else:
            ValidationError.set_invocation_command('python')

        args = sys.argv[1:]
        dice = DiceParser.parse(args)
        
        ui = GameUI()
        crypto = CryptoProvider()
        help_gen = HelpTableGenerator()
        interaction = FairInteraction(crypto, ui)
        
        controller = GameController(dice, ui, interaction, help_gen)
        controller.run()

    except ValidationError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nGame interrupted. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()