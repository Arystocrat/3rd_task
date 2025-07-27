import sys
import secrets
import hmac
import hashlib
from tabulate import tabulate

# ==============================================================================
# 1. Error Handling Class
# ==============================================================================

class ValidationError(Exception):
    """
    Custom exception for argument validation errors.
    Provides a formatted message including an example of correct usage.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        # Dynamically get the script name for the example usage
        script_name = sys.argv[0] if sys.argv else 'game.py'
        example = f"python {script_name} 2,2,4,4,9,9 1,1,6,6,8,8 3,3,5,5,7,7"
        return f"\nArgument Error: {self.message}\n\nExample usage:\n{example}\n"

# Predefined error instances for extension without modification
ValidationError.NOT_ENOUGH_DICE = ValidationError("Please specify at least three dice.")
ValidationError.INCONSISTENT_FACES = ValidationError("All dice must have the same number of faces.")
ValidationError.NON_INTEGER_VALUE = ValidationError("All dice faces must be integer values.")


# ==============================================================================
# 2. Data Structure for a Die
# ==============================================================================

class Die:
    """Represents a single die with a list of face values."""
    def __init__(self, faces: list[int]):
        if not faces:
            # This case should be caught by INCONSISTENT_FACES check, but as a safeguard:
            raise ValueError("A die must have at least one face.")
        self.faces = faces

    def __str__(self) -> str:
        """Returns a string representation like '1,2,3,4,5,6'."""
        return ",".join(map(str, self.faces))

    def __len__(self) -> int:
        """Returns the number of faces on the die."""
        return len(self.faces)


# ==============================================================================
# 3. Command-Line Argument Parser
# ==============================================================================

class DiceParser:
    """Parses and validates command-line arguments to create Die objects."""
    @staticmethod
    def parse(args: list[str]) -> list[Die]:
        """
        Parses a list of string arguments into a list of Die objects.
        Raises ValidationError on failure.
        """
        if len(args) < 3:
            raise ValidationError.NOT_ENOUGH_DICE

        dice_list = []
        try:
            for arg_string in args:
                # Handle potential empty strings from trailing commas
                faces = [int(f) for f in arg_string.split(',') if f]
                dice_list.append(Die(faces))
        except ValueError:
            raise ValidationError.NON_INTEGER_VALUE

        first_die_faces = len(dice_list[0])
        if not all(len(d) == first_die_faces for d in dice_list):
            raise ValidationError.INCONSISTENT_FACES

        return dice_list


# ==============================================================================
# 4. Cryptographic Operations Provider
# ==============================================================================

class CryptoProvider:
    """Provides cryptographic functionalities like key generation and HMAC calculation."""
    @staticmethod
    def generate_key() -> bytes:
        """Generates a cryptographically secure 256-bit (32-byte) key."""
        return secrets.token_bytes(32)

    @staticmethod
    def generate_secure_random(max_val: int) -> int:
        """Generates a secure, uniformly distributed random integer in [0, max_val-1]."""
        return secrets.randbelow(max_val)

    @staticmethod
    def calculate_hmac(key: bytes, message_int: int) -> str:
        """Calculates HMAC-SHA3-256 for a given integer message and key."""
        # Convert integer to a consistent byte representation for HMAC
        message_bytes = str(message_int).encode('utf-8')
        h = hmac.new(key, message_bytes, hashlib.sha3_256)
        return h.hexdigest().upper()


# ==============================================================================
# 5. Probability Calculation Logic
# ==============================================================================

class ProbabilityCalculator:
    """Calculates win probabilities between two dice."""
    @staticmethod
    def calculate_win_probability(die1: Die, die2: Die) -> float:
        """Calculates the probability of die1 winning against die2."""
        wins = 0
        total_outcomes = len(die1) * len(die2)
        if total_outcomes == 0:
            return 0.0

        for face1 in die1.faces:
            for face2 in die2.faces:
                if face1 > face2:
                    wins += 1
        
        return wins / total_outcomes


# ==============================================================================
# 6. Help Table Generation
# ==============================================================================

class HelpTableGenerator:
    """Generates a formatted ASCII table of win probabilities."""
    @staticmethod
    def generate_table(all_dice: list[Die], calculator: ProbabilityCalculator) -> str:
        """Creates the help table showing win probabilities for the USER."""
        headers = ["v PC | User >"] + [str(d) for d in all_dice]
        table_data = []

        for user_die in all_dice:
            row = [str(user_die)]
            for pc_die in all_dice:
                if user_die is pc_die:
                    # Probability of winning against oneself
                    prob = calculator.calculate_win_probability(user_die, pc_die)
                    row.append(f"*{float(prob):.4f}*")
                else:
                    prob = calculator.calculate_win_probability(user_die, pc_die)
                    row.append(f"{float(prob):.4f}")
            table_data.append(row)
        
        intro_text = (
            "\n--- Win Probability Table ---\n"
            "This table shows the probability of the User's die (rows) winning against the PC's die (columns).\n"
            "* Diagonal values show probability of a die winning against an identical one.\n"
        )
        return intro_text + tabulate(table_data, headers=headers, tablefmt="grid")


# ==============================================================================
# 7. Console User Interface
# ==============================================================================

class GameUI:
    """Handles all console input and output."""
    def display_message(self, text: str):
        print(text)

    def display_hmac(self, hmac_hex: str):
        print(f"HMAC: {hmac_hex}")

    def display_key_and_move(self, key: bytes, move: int, name: str = "My"):
        print(f"{name} move was: {move} (Secret Key: {key.hex().upper()})")

    def get_user_choice(self, prompt: str, options: list[str], allow_help: bool = True) -> str:
        """Displays a menu and gets a validated choice from the user."""
        while True:
            print(f"\n{prompt}")
            for i, option in enumerate(options):
                print(f" {i+1} - {option}")
            
            print("\n 0 - Exit")
            if allow_help:
                print(" ? - Help")

            choice = input("Your choice: ").strip().lower()

            if choice == '0':
                print("Exiting game. Goodbye!")
                sys.exit(0)
            if choice == '?' and allow_help:
                return '?'
            
            try:
                choice_int = int(choice)
                if 1 <= choice_int <= len(options):
                    return str(choice_int - 1)  # Return zero-based index
                else:
                    print("Invalid choice. Please enter a number from the list.")
            except ValueError:
                print("Invalid input. Please enter a number, '?' or '0'.")


# ==============================================================================
# 8. Provably Fair Random Number Generation Protocol
# ==============================================================================

class FairRandomGenerator:
    """Implements the provably fair random number generation protocol."""
    def __init__(self, crypto_provider: CryptoProvider, ui: GameUI):
        self.crypto = crypto_provider
        self.ui = ui

    def generate(self, max_val: int, prompt: str) -> int:
        """
        Executes one full round of fair random generation.
        Returns the final resulting integer.
        """
        computer_move = self.crypto.generate_secure_random(max_val)
        key = self.crypto.generate_key() # Generate a new key for every single interaction
        hmac = self.crypto.calculate_hmac(key, computer_move)

        self.ui.display_message(f"I have made my choice in range [0..{max_val-1}].")
        self.ui.display_hmac(hmac)

        options = [str(i) for i in range(max_val)]
        while True:
            user_move_str = self.ui.get_user_choice(prompt, options, allow_help=False)
            if user_move_str.isdigit():
                break
        user_move = int(user_move_str)
        
        result = (computer_move + user_move) % max_val
        
        self.ui.display_key_and_move(key, computer_move)
        self.ui.display_message(f"Result: ({computer_move} + {user_move}) mod {max_val} = {result}")
        return result


# ==============================================================================
# 9. Main Game Controller
# ==============================================================================

class GameController:
    """Orchestrates the main game flow."""
    def __init__(self, dice: list[Die], ui: GameUI, random_gen: FairRandomGenerator, help_gen: HelpTableGenerator):
        self.all_dice = dice
        self.ui = ui
        self.random_gen = random_gen
        self.help_gen = help_gen

    def run(self):
        """Starts and manages the game session."""
        self.ui.display_message("--- Welcome to the Non-Transitive Dice Game! ---")
        
        while True:
            self._play_round()
            
            play_again = input("\nPlay another round? (y/n): ").strip().lower()
            if play_again != 'y':
                self.ui.display_message("Thanks for playing!")
                break

    def _play_round(self):
        # 1. Determine who moves first
        self.ui.display_message("\nLet's determine who picks a die first.")
        # User wins the toss if the result is 0, computer wins if it's 1
        first_move_result = self.random_gen.generate(2, "Enter 0 or 1. If you match my secret bit, you go first:")
        user_goes_first = (first_move_result == 0)

        # 2. Dice Selection
        player_die, computer_die = self._select_dice(user_goes_first)

        self.ui.display_message(f"\nYour die: [{player_die}]")
        self.ui.display_message(f"My die:  [{computer_die}]")

        # 3. Rolls
        num_faces = len(player_die)
        self.ui.display_message("\n--- Time to roll! ---")
        
        # Computer's roll
        self.ui.display_message("\nMy roll:")
        computer_roll_index = self.random_gen.generate(num_faces, f"Enter your number (0-{num_faces-1}) for my roll:")
        computer_roll_value = computer_die.faces[computer_roll_index]
        self.ui.display_message(f"My roll result is face #{computer_roll_index} -> {computer_roll_value}")

        # Player's roll
        self.ui.display_message("\nYour roll:")
        player_roll_index = self.random_gen.generate(num_faces, f"Enter your number (0-{num_faces-1}) for your roll:")
        player_roll_value = player_die.faces[player_roll_index]
        self.ui.display_message(f"Your roll result is face #{player_roll_index} -> {player_roll_value}")
        
        # 4. Determine Winner
        self.ui.display_message("\n--- Results ---")
        self.ui.display_message(f"You rolled {player_roll_value}, I rolled {computer_roll_value}.")
        if player_roll_value > computer_roll_value:
            self.ui.display_message("You win!")
        elif computer_roll_value > player_roll_value:
            self.ui.display_message("I win!")
        else:
            self.ui.display_message("It's a draw!")
    
    def _select_dice(self, user_goes_first: bool):
        available_dice = list(self.all_dice)
        
        if user_goes_first:
            self.ui.display_message("\nYou get to choose first.")
            player_die = self._get_player_die_choice(available_dice)
            available_dice.remove(player_die)
            computer_die = secrets.choice(available_dice)
            self.ui.display_message(f"I've chosen my die from the rest.")
        else:
            self.ui.display_message("\nI get to choose first.")
            computer_die = secrets.choice(available_dice)
            self.ui.display_message(f"I have chosen my die.")
            available_dice.remove(computer_die)
            player_die = self._get_player_die_choice(available_dice)

        return player_die, computer_die
    
    def _get_player_die_choice(self, available_dice: list[Die]):
        while True:
            options = [str(d) for d in available_dice]
            choice_str = self.ui.get_user_choice("Choose your die from the list:", options, allow_help=True)
            
            if choice_str == '?':
                table = self.help_gen.generate_table(self.all_dice, ProbabilityCalculator)
                self.ui.display_message(f"\n{table}")
                continue # Show menu again after help
            
            return available_dice[int(choice_str)]


# ==============================================================================
# 10. Main Execution Block
# ==============================================================================

def main():
    """
    The main entry point of the application.
    Parses arguments, sets up components, and starts the game.
    """
    try:
        # 1. Parse and validate arguments from command line (excluding script name)
        args = sys.argv[1:]
        dice = DiceParser.parse(args)

        # 2. Set up all components (Dependency Injection)
        ui = GameUI()
        crypto = CryptoProvider()
        help_gen = HelpTableGenerator()
        # The calculator can be used statically, so no instance needed for the controller
        random_gen = FairRandomGenerator(crypto, ui)
        
        # 3. Initialize and run the game controller
        controller = GameController(dice, ui, random_gen, help_gen)
        controller.run()

    except ValidationError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nGame interrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
