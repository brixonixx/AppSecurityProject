import shelve
from testrun2 import User  # Ensure this matches the actual path to your User class

def update_user_data():
    """Ensure all user objects in the database have the 'redeemed_rewards' attribute."""
    with shelve.open('user_data.db', 'c') as db:
        users = db.get('users', {})
        for user_id, user in users.items():
            if not hasattr(user, 'redeemed_rewards'):  # Check if the attribute is missing
                user.redeemed_rewards = []  # Add the missing attribute
                print(f"Updated user {user_id}: Added 'redeemed_rewards'.")
            users[user_id] = user  # Save the updated user back into the database
        db['users'] = users  # Save the updated users dictionary
    print("All user data has been updated.")

# Call the function to update the database
update_user_data()
with shelve.open('user_data.db', 'r') as db:
    users = db.get('users', {})
    for user_id, user in users.items():
        print(f"User {user_id}: Redeemed Rewards -> {user.redeemed_rewards}")
