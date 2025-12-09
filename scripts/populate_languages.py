#!/usr/bin/env python3
"""
Script to populate the languages table with 60 supported languages.
Clears existing data and inserts fresh records with native script names.

Usage: python populate_languages.py
"""

from app import create_app
from models import db
from models.language import Language


def populate_languages():
    """Populate the languages table with all supported languages"""

    # Language data: (code, original_name, en_name, display_order)
    # Sorted alphabetically by English name
    languages_data = [
        ('af', 'Afrikaans', 'Afrikaans', 1),
        ('am', 'አማርኛ', 'Amharic', 2),
        ('ar', 'العربية', 'Arabic', 3),
        ('hy', 'Հայերեն', 'Armenian', 4),
        ('az', 'Azərbaycan', 'Azerbaijani', 5),
        ('be', 'Беларуская', 'Belarusian', 6),
        ('bn', 'বাংলা', 'Bengali', 7),
        ('zh-CN', '简体中文', 'Chinese (Simplified)', 8),
        ('zh-TW', '繁體中文', 'Chinese (Traditional)', 9),
        ('cs', 'Čeština', 'Czech', 10),
        ('da', 'Dansk', 'Danish', 11),
        ('nl', 'Nederlands', 'Dutch', 12),
        ('en', 'English', 'English', 13),
        ('et', 'Eesti', 'Estonian', 14),
        ('fi', 'Suomi', 'Finnish', 15),
        ('fr', 'Français', 'French', 16),
        ('ka', 'ქართული', 'Georgian', 17),
        ('de', 'Deutsch', 'German', 18),
        ('el', 'Ελληνικά', 'Greek', 19),
        ('gu', 'ગુજરાતી', 'Gujarati', 20),
        ('ha', 'Hausa', 'Hausa', 21),
        ('he', 'עברית', 'Hebrew', 22),
        ('hi', 'हिन्दी', 'Hindi', 23),
        ('hu', 'Magyar', 'Hungarian', 24),
        ('id', 'Bahasa Indonesia', 'Indonesian', 25),
        ('it', 'Italiano', 'Italian', 26),
        ('ja', '日本語', 'Japanese', 27),
        ('kn', 'ಕನ್ನಡ', 'Kannada', 28),
        ('kk', 'Қазақша', 'Kazakh', 29),
        ('ko', '한국어', 'Korean', 30),
        ('ky', 'Кыргызча', 'Kyrgyz', 31),
        ('lv', 'Latviešu', 'Latvian', 32),
        ('lt', 'Lietuvių', 'Lithuanian', 33),
        ('ml', 'മലയാളം', 'Malayalam', 34),
        ('no', 'Norsk', 'Norwegian', 35),
        ('fa', 'فارسی', 'Persian', 36),
        ('pl', 'Polski', 'Polish', 37),
        ('pt', 'Português', 'Portuguese', 38),
        ('ro', 'Română', 'Romanian', 39),
        ('ru', 'Русский', 'Russian', 40),
        ('sr', 'Српски', 'Serbian', 41),
        ('so', 'Soomaali', 'Somali', 42),
        ('es', 'Español', 'Spanish', 43),
        ('sw', 'Kiswahili', 'Swahili', 44),
        ('sv', 'Svenska', 'Swedish', 45),
        ('tg', 'Тоҷикӣ', 'Tajik', 46),
        ('ta', 'தமிழ்', 'Tamil', 47),
        ('te', 'తెలుగు', 'Telugu', 48),
        ('th', 'ไทย', 'Thai', 49),
        ('tr', 'Türkçe', 'Turkish', 50),
        ('tk', 'Türkmençe', 'Turkmen', 51),
        ('uk', 'Українська', 'Ukrainian', 52),
        ('ur', 'اردو', 'Urdu', 53),
        ('uz', 'Oʻzbekcha', 'Uzbek', 54),
        ('vi', 'Tiếng Việt', 'Vietnamese', 55),
        ('xh', 'isiXhosa', 'Xhosa', 56),
        ('yo', 'Yorùbá', 'Yoruba', 57),
        ('zu', 'isiZulu', 'Zulu', 58),
    ]

    app = create_app()

    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        print(f"\nClearing existing languages...")
        deleted_count = Language.query.delete()
        print(f"Deleted {deleted_count} existing language(s)")

        print(f"\nInserting {len(languages_data)} languages...")

        inserted_count = 0
        for code, original_name, en_name, display_order in languages_data:
            language = Language(
                code=code,
                original_name=original_name,
                en_name=en_name,
                display_order=display_order
            )
            db.session.add(language)
            inserted_count += 1
            print(f"  [{display_order:2d}] {code:6s} - {en_name:25s} ({original_name})")

        try:
            db.session.commit()
            print(f"\n✓ Successfully inserted {inserted_count} languages!")

            # Verify the insertion
            total_languages = Language.query.count()
            print(f"✓ Database now contains {total_languages} languages")

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error occurred: {e}")
            raise


if __name__ == '__main__':
    populate_languages()
