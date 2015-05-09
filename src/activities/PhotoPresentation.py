# coding=utf-8
__author__ = 'nico'

import os

from activities.AbstractActivity import AbstractActivity
from player.PhotoPresentationPlayer import PhotoPresentationPlayer
from config import SUPPORTED_IMG_EXTENSIONS


class PhotoPresentation(AbstractActivity):
    name = "Photo presentation"

    def __init__(self, id, name, random, gap, tags):
        AbstractActivity.__init__(self, id, name)
        self.random = random
        self.gap = gap
        self.tags = tags

        self.player = None

    def run(self, writer):
        PhotoPresentationPlayer(self.gap, self.random, self.tags).play(writer)

    def __str__(self):
        toret = "Photo presentation acivity:\n" \
                "Id: {id}\n" \
                "Name: {name}\n" \
                "Random: {random}\n" \
                "Gap: {gap}\n".format(id=self.id,
                                      name=self.name,
                                      random=self.random,
                                      gap=self.gap)
        for tag in self.tags:
            toret += "Photo presentation tag:\n" \
                     "\tName: {name}\n" \
                     "\tPath: {path}\n" \
                     "\tSound associated: {sound_associated}\n".format(name=tag.name,
                                                                       path=tag.path,
                                                                       sound_associated=tag.sound_associated)
            for sound in tag.sounds:
                toret += "\tSound:\n" \
                         "\t\tPath: {path}\n".format(path=sound.path)
        return toret


class PhotoPresentationTag(object):
    def __init__(self, name, path, associated_sound, sounds=[]):
        self.name = name
        self.path = path
        self.associated_sound = associated_sound
        self.sounds = sounds

    def check_files(self):
        images = [os.path.join(self.path, img) for img in os.listdir(self.path) if
                  img.endswith(SUPPORTED_IMG_EXTENSIONS)]
        if len(images) == 0:
            return False
        for sound in self.sounds:
            if not os.path.isfile(sound.path):
                return False
        return True


class Sound(object):
    def __init__(self, path):
        self.path = path
