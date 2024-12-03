from courses import models
from django.shortcuts import get_object_or_404
import logging
import csv
logger = logging.getLogger(__name__)

class ChapterVideoHelper():

    @staticmethod
    def submit_rating(id: int, rating: float, user):
        chapter_video = get_object_or_404(models.ChapterVideo, id=id)
        
        try:    
            user_rating_object = models.UserRatingOnChapter.objects.create(
                chapter_video = chapter_video,
                user = user,
                rating = rating
            )
            user_rating_object.update_avg_rating()
        except Exception as e:
            logger.info (f"Failed to rate due to exception {e}")
            # DO nothing if user has already rated this video
            pass

        return True

    @staticmethod
    def upload_bulk_file(csv_file):
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        total_success = 0
        failed_rows = []
        for idx, row in enumerate(reader):
            try:
                chapter_id = row.get("chapter_id")
                url = row.get("url")
                description = row.get("description")
                models.ChapterVideo.objects.create(
                    chapter_id=chapter_id,
                    url = url,
                    description = description
                )
                total_success += 1
            except Exception as e:  
                failed_rows.append(idx)
                logger.info (f"Failed to upload chapter url {url} for id {chapter_id}")
        return total_success, failed_rows
