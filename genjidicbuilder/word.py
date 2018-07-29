# -*- coding: utf-8 -*-
# Copyright (c) 2018 Masahiko Hashimoto <hashimom@geeko.jp>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import subprocess
import csv
import jaconv
from pymongo import MongoClient

mongodbHostName = 'localhost'
mongodbPortNo = 27017
maxcost = 1000

basickeys = [
    "あ", "い", "う", "え", "お",
    "か", "き", "く", "け", "こ",
    "さ", "し", "す", "せ", "そ",
    "た", "ち", "つ", "て", "と",
    "な", "に", "ぬ", "ね", "の",
    "は", "ひ", "ふ", "へ", "ほ",
    "ま", "み", "む", "め", "も",
    "や", "ゆ", "よ",
    "ら", "り", "る", "れ", "ろ",
    "わ", "を", "ん",
    "が", "ぎ", "ぐ", "げ", "ご",
    "ざ", "じ", "ず", "ぜ", "ぞ",
    "だ", "ぢ", "づ", "で", "ど",
    "ば", "び", "ぶ", "べ", "ぼ",
    "ぱ", "ぴ", "ぷ", "ぺ", "ぽ",
    "ぁ", "ぃ", "ぅ", "ぇ", "ぉ",
    "ゃ", "ゅ", "ょ", "っ",
    "１", "２", "３", "４", "５", "６", "７", "８", "９", "０",
    "、", "。", "ー", "＋", "！", "＆", "（", "）", "｛", "｝"
]

class Word:
    def __init__(self, naistjdicpath):
        client = MongoClient(mongodbHostName, mongodbPortNo)
        db = client.kasuga
        self.words = db.words
        self.phases = db.phases

        db = client.genji
        self.dic = db.dic
        # 一旦 GenjiDic のコレクションは削除して新規作成する
        self.dic.remove()
        self.naistjdicpath = naistjdicpath

        # naist-jdic.csv のファイルパス指定（ない場合は None にする必要がある）
#        self.naistjdic = db.naistjdic
#        self.naistjdicpath = naistjdicpath
#        if naistjdicpath:
#            self.naistjdic.remove()

    def readNaistJdic(self):
        # Naist-Jdic の読み込み
        f = open(self.naistjdicpath, "r")
        reader = csv.reader(f)
        print("Naist-jdic regist START!")
        for row in reader:
            if row[11] != "":
                self.dic.insert({"key": row[0], "read": jaconv.kata2hira(row[11]), "cost": maxcost, "from": "naistjdic"})

    def regist(self):
        # Naist-Jdic ファイルパス指定がある場合はここで登録
        #if self.naistjdicpath:
        self.readNaistJdic()

        # 基本語登録
        for basickey in basickeys:
            self.dic.insert({"key": basickey, "read": basickey, "cost": maxcost, "from": "basic"})

        # 単語取得
        for word in self.words.find():
            print("regist: " + word["surface"])
            # 単単語登録
            if self.dic.find({"key": word["surface"], "read": word["read"], "from": "kasuga"}).count() == 0:
                self.dic.insert({"key": word["surface"], "read": word["read"], "cost": maxcost})

                # 文節取得
                keycnt = self.phases.find({"Independent.surface": word["surface"]}).count()
                yomcnt = self.phases.find({"Independent.read": word["read"]}).count()
                for phase in self.phases.find({"Independent.surface": word["surface"]}):
                    # 文節・キー部 / 該当文節数取得
                    if phase["Ancillary"] != None:
                        phasekey = phase["Independent"]["surface"] + phase["Ancillary"]["surface"]
                        phasecnt = self.phases.find({
                            "Independent.surface": phase["Independent"]["surface"],
                            "Ancillary.surface": phase["Ancillary"]["surface"]}).count()
                    else:
                        phasekey = phase["Independent"]["surface"]
                        phasecnt = self.phases.find({
                            "Independent.surface": phase["Independent"]["surface"]}).count()

                    if self.dic.find({"key": phasekey}).count() == 0:
                        # 文節・読み部 / コスト取得
                        phaseyomi = phase["Independent"]["read"] + phase["Ancillary"]["read"]
                        phasecost = (1 - ((keycnt / yomcnt) * (phasecnt / keycnt))) * maxcost

                        # 文節を辞書へ登録
                        self.dic.insert({"key": phasekey, "read": phaseyomi, "cost": int(phasecost), "from": "kasuga"})

        # CSV出力
        print("CSV output START!")
        subprocess.call(["mongoexport", "-h", mongodbHostName, "--port", str(mongodbPortNo),
                         "-d", "genji", "-c", "dic",
                         "--csv", "--out", "genjidic.csv", "--noHeaderLine",
                         "--fields", "cost,key,read"])


