from sqlalchemy.orm import Session
from .models import Word, User

def add_word(db: Session, word: str, translation: str, example: str = None):
    """
    Adds a new word with its translation and an optional example to the database.

    This method creates a new `Word` object with the given word, translation, and example,
    then adds it to the database. The word is committed and the newly created word object
    is returned after the commit.

    Parameters:
    db (Session): The database session used to interact with the database.
    word (str): The word to add to the database.
    translation (str): The translation of the word.
    example (str, optional): An example sentence using the word. Defaults to None.

    Returns:
    Word: The newly added word object with its data after being saved in the database.
    """
    new_word = Word(word=word, translation=translation, example=example)
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    return new_word

def update_word(db: Session, word: str, translation: str = None, example: str = None):
    """
    Updates an existing word's translation and/or example in the database.

    This method looks up a word by its name, and if the word is found,
    updates the translation and/or example based on the provided arguments.
    The updated word object is returned after the commit, or `None` if the word is not found.

    Parameters:
    db (Session): The database session used to interact with the database.
    word (str): The word to update in the database.
    translation (str, optional): The new translation of the word. Defaults to None.
    example (str, optional): The new example sentence using the word. Defaults to None.

    Returns:
    Word or None: The updated word object if found and updated, otherwise `None`.
    """
    db_word = db.query(Word).filter(Word.word == word).first()
    if db_word:
        if translation:
            db_word.translation = translation
        if example:
            db_word.example = example
        db.commit()
        return db_word
    return None

def add_user(db: Session, username: str, email: str):
    """
    Adds a new user to the database.

    This method creates a new `User` object with the given username and email,
    then adds it to the database. The user is committed and the newly created user object
    is returned after the commit.

    Parameters:
    db (Session): The database session used to interact with the database.
    username (str): The username of the new user.
    email (str): The email address of the new user.

    Returns:
    User: The newly added user object with its data after being saved in the database.
    """
    new_user = User(username=username, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user(db: Session, username: str):
    """
    Retrieves a user by their username from the database.

    This method queries the database for a user by the provided username and
    returns the user object if found, or `None` if the user does not exist.

    Parameters:
    db (Session): The database session used to interact with the database.
    username (str): The username of the user to retrieve.

    Returns:
    User or None: The user object if found, otherwise `None`.
    """
    return db.query(User).filter(User.username == username).first()