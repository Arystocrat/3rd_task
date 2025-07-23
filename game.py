import sys
import os
import hmac
import hashlib
import secrets
from tabulate import tabulate

# -----------------------------------------------------------------------------
# 1. ABSTRACTION FOR A SINGLE DIE
# -----------------------------------------------------------------------------
class Dice:
    """Represents a single die with a specific set of faces."""
    def __init__(self, faces: list[int]):
        if not faces:
            raise ValueError("A die must have at least one face.")
        self.faces = faces

    def roll(self, index: int) -> int:
        """Returns the value of a face at a given index."""
        return self.faces[index]

    def __str__(self) -> str:
        return f"[{','.join(map(str, self.faces))}]"

# -----------------------------------------------------------------------------
# 2. CRYPTOGRAPHIC OPERATIONS
# -----------------------------------------------------------------------------
class Crypto:
    """Handles secure key generation and HMAC calculation."""
    def generate_key(self, bits: int = 256) -> bytes:
        """Generates a cryptographically secure random key."""
        return os.urandom(bits // 8)

    def calculate_hmac(self, key: bytes, message: bytes) -> str:
        """Calculates HMAC-SHA3-256 for a given message and key."""
        return hmac.new(key, message, hashlib.sha3_256).hexdigest().upper()

# -----------------------------------------------------------------------------
# 3. PROVABLY FAIR RANDOM NUMBER GENERATION PROTOCOL
# -----------------------------------------------------------------------------
class FairRandom:
    """Implements the protocol for provably fair random number generation."""
    def __init__(self, crypto: Crypto, ui):
        self._crypto = crypto
        self._ui = ui

    def generate(self, max_value: int) -> int | None:
        """
        Executes the fair random generation protocol for a number in [0, max_value].
        Returns the generated number or None if the user exits.
        """
        range_size = max_value + 1
        
        # 1. Computer generates a secret key and a random number
        key = self._crypto.generate_key()
        computer_num = secrets.randbelow(range_size)
        
        # 2. Computer calculates and displays HMAC
        # Message must be bytes. We'll use 8 bytes, which is plenty for our range.
        message_bytes = computer_num.to_bytes(8, 'big')
        hmac_val = self._crypto.calculate_hmac(key, message_bytes)
        
        print(f"I selected a random value in the range 0..{max_value} (HMAC={hmac_val}).")
        
        # 3. User selects their number
        options = {i: str(i) for i in range(range_size)}
        user_choice = self._ui.prompt_user("Add your number:", options, show_help=False)

        if user_choice is None: # User chose to exit
            return None
        
        user_num = int(user_choice)
            
        # 4. Calculate final result and reveal computer's choices
        final_result = (computer_num + user_num) % range_size
        
        print(f"My number is {computer_num} (KEY={key.hex().upper()}).")
        print(f"The fair number generation result is {computer_num} + {user_num} = {final_result} (mod {range_size}).")
        
        return final_result

# -----------------------------------------------------------------------------
# 4. PROBABILITY CALCULATIONS
# -----------------------------------------------------------------------------
class ProbabilityCalculator:
    """Calculates the win probability between two dice."""
    def calculate_win_probability(self, dice1: Dice, dice2: Dice) -> float:
        """Calculates the probability of dice1 winning against dice2."""
        wins1 = 0
        total_outcomes = len(dice1.faces) * len(dice2.faces)
        
        for face1 in dice1.faces:
            for face2 in dice2.faces:
                if face1 > face2:
                    wins1 += 1
        
        return wins1 / total_outcomes

# -----------------------------------------------------------------------------
# 5. HELP TABLE GENERATION
# -----------------------------------------------------------------------------
class HelpTable:
    """Generates and displays the win probability table."""
    def __init__(self, dice_list: list[Dice], calculator: ProbabilityCalculator):
        self._dice = dice_list
        self._calculator = calculator

    def display(self):
        """Prints the formatted help table to the console."""
        headers = ["User dice v"] + [str(d) for d in self._dice]
        table_data = []

        for row_dice in self._dice:
            row = [str(row_dice)]
            for col_dice in self._dice:
                prob = self._calculator.calculate_win_probability(row_dice, col_dice)
                # Format diagonal differently as requested
                if row_dice is col_dice:
                    row.append(f".{int(prob * 10000):<4}") # Example: .3333
                else:
                    row.append(f"{prob:.4f}")
            table_data.append(row)

        print("\nProbability of the win for the user (row dice vs column dice):")
        print(tabulate(table_data, headers=headers, tablefmt="grid", numalign="center"))
        print()

# -----------------------------------------------------------------------------
# 6. COMMAND-LINE ARGUMENT PARSING
# -----------------------------------------------------------------------------
class ArgsParser:
    """Parses and validates command-line arguments."""
    def parse(self, args: list[str]) -> list[Dice] | None:
        """
        Parses arguments into a list of Dice objects.
        Returns the list or None if validation fails.
        """
        try:
            if len(args) < 3:
                raise ValueError("At least 3 dice are required.")

            parsed_dice = []
            num_faces = 0
            for i, arg_str in enumerate(args):
                faces_str = arg_str.split(',')
                faces_int = [int(f) for f in faces_str]
                
                if i == 0:
                    num_faces = len(faces_int)
                    if num_faces == 0:
                         raise ValueError("Dice cannot have 0 faces.")
                elif len(faces_int) != num_faces:
                    raise ValueError("All dice must have the same number of faces.")
                
                parsed_dice.append(Dice(faces_int))
            return parsed_dice
        except ValueError as e:
            print(f"Error: Invalid arguments. {e}")
            print("Example: python game.py 2,2,4,4,9,9 1,1,6,6,8,8 3,3,5,5,7,7")
            return None
        except Exception:
            print("Error: Invalid format in dice configuration.")
            print("Please provide dice as comma-separated integers.")
            print("Example: python game.py 2,2,4,4,9,9 1,1,6,6,8,8 3,3,5,5,7,7")
            return None

# -----------------------------------------------------------------------------
# 7. USER INTERFACE
# -----------------------------------------------------------------------------
class UI:
    """Handles all user interaction, including menus."""
    def __init__(self, help_table: HelpTable | None = None):
        self._help_table = help_table

    def prompt_user(self, prompt: str, options: dict, show_help=True) -> str | None:
        """
        Displays a menu and gets a valid choice from the user.
        Returns the choice, or None if the user exits.
        """
        while True:
            print(prompt)
            for key, value in options.items():
                print(f"{key} - {value}")
            print("X - exit")
            if show_help:
                print("? - help")
            
            selection = input("Your selection: ").strip().upper()
            
            if selection == 'X':
                return None
            if selection == '?' and show_help:
                if self._help_table:
                    self._help_table.display()
                else:
                    print("No help available at this moment.")
                continue
            
            # Check if the key is a valid option
            # We convert keys to str for comparison as input is a string.
            valid_keys = [str(k) for k in options.keys()]
            if selection in valid_keys:
                return selection

            print("Invalid selection, please try again.")


# -----------------------------------------------------------------------------
# 8. MAIN GAME LOGIC
# -----------------------------------------------------------------------------
class Game:
    """Orchestrates the entire game flow."""
    def __init__(self, dice_list: list[Dice]):
        self._dice = dice_list
        self._crypto = Crypto()
        
        # Dependencies for other classes
        calculator = ProbabilityCalculator()
        help_table = HelpTable(self._dice, calculator)
        self._ui = UI(help_table)
        self._fair_random = FairRandom(self._crypto, self._ui)
        self._num_faces = len(self._dice[0].faces) if self._dice else 0


    def run(self):
        """Starts and manages the game session."""
        print("Let's determine who makes the first move.")
        first_move_result = self._fair_random.generate(1)

        if first_move_result is None:
            print("Game exited.")
            return

        is_user_first = (first_move_result == 0) # User wins the toss if the result is 0 (their guess)
        
        if is_user_first:
            print("You won the toss! You make the first move.")
            self._player_turn_sequence(player_is_first=True)
        else:
            print("I won the toss. I make the first move.")
            self._player_turn_sequence(player_is_first=False)

    def _player_turn_sequence(self, player_is_first: bool):
        """Handles the sequence of players choosing dice."""
        available_dice = self._dice.copy()
        
        if player_is_first:
            user_dice = self._get_user_dice_choice(available_dice)
            if user_dice is None: return
            available_dice.remove(user_dice)
            computer_dice = self._get_computer_dice_choice(available_dice)
        else:
            computer_dice = self._get_computer_dice_choice(available_dice)
            print(f"I choose the {computer_dice} dice.")
            available_dice.remove(computer_dice)
            user_dice = self._get_user_dice_choice(available_dice)
            if user_dice is None: return

        print(f"You chose the {user_dice} dice.")
        self._perform_rolls(user_dice, computer_dice)


    def _get_user_dice_choice(self, choices: list[Dice]) -> Dice | None:
        """Prompts the user to select a die from the available list."""
        options = {i: str(d) for i, d in enumerate(choices)}
        choice = self._ui.prompt_user("Choose your dice:", options)
        return choices[int(choice)] if choice is not None else None

    def _get_computer_dice_choice(self, choices: list[Dice]) -> Dice:
        """Computer's 'strategy' for choosing a die (chooses randomly)."""
        return secrets.choice(choices)

    def _perform_rolls(self, user_dice: Dice, computer_dice: Dice):
        """Performs the fair rolls for both user and computer."""
        print("\nIt's time for my roll.")
        comp_roll_index = self._fair_random.generate(self._num_faces - 1)
        if comp_roll_index is None: return
        comp_roll_value = computer_dice.roll(comp_roll_index)
        print(f"My roll result is {comp_roll_value}.")
        
        print("\nIt's time for your roll.")
        user_roll_index = self._fair_random.generate(self._num_faces - 1)
        if user_roll_index is None: return
        user_roll_value = user_dice.roll(user_roll_index)
        print(f"Your roll result is {user_roll_value}.")

        # Determine and announce the winner
        print("\n--- RESULTS ---")
        if user_roll_value > comp_roll_value:
            print(f"You win ({user_roll_value} > {comp_roll_value})!")
        elif comp_roll_value > user_roll_value:
            print(f"I win ({comp_roll_value} > {user_roll_value})!")
        else:
            print(f"It's a draw ({user_roll_value} == {comp_roll_value})!")
        print("---------------")

# -----------------------------------------------------------------------------
# 9. SCRIPT ENTRY POINT
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = ArgsParser()
    dice = parser.parse(sys.argv[1:])
    
    if dice:
        game = Game(dice)
        game.run()