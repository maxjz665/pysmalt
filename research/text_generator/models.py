from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Magazine(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class TextList(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Text(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, blank=True)
    magazine = models.ForeignKey(Magazine, on_delete=models.CASCADE, null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    content = models.TextField()  # Текст
    text_list = models.ForeignKey(TextList, on_delete=models.CASCADE, related_name='texts')

    def __str__(self):
        return self.title