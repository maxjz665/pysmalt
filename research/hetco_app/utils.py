import numpy as np
import csv
import xlsxwriter
import math


class HetcoUtils:
    def __init__(self):
        # Инициализация переменных класса
        self.xlsxNAME = 'exp3t.xlsx'
        self.AUTHOR = 'EXP3'
        self.allText = [154, 159]  # Список текстов
        self.trainText = [154]  # Обучающие тексты
        self.COUNT = len(self.allText)
        self.LENGTH = 500  # Длина отрывка в словах
        self.SENT = 30  # Количество предложений в отрывке

        self.parts = ["существительное", "прилагательное", "числительное", "местоимение", "глагол",
                      "причастие", "деепричастие", "наречие", "кат.состояния", "частица",
                      "предлог", "союз", "модальное", "междометие", "звукоподражательное",
                      "иностранное", "цитата", "вводное", "старославянизм", "фразеологизм",
                      "неязыковой", "сокращённое", "многочленное", "заголовок"]
        self.partLen = len(self.parts)

    def get_part_of_speech(self, word):
        """Заглушка для определения части речи."""
        return "неизвестно"  # Пока возвращаем заглушку

    def read_data(self):
        """Чтение данных из CSV-файлов."""
        self.data = []
        self.name = []
        for text in range(self.COUNT):
            self.data.append([])
            sentFlag = True
            sentence = []
            sentCounter = 0
            wordCounter = 0
            self.name.append([])
            with open(f"{self.AUTHOR}_csv/{self.allText[text]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    row[1] = row[1].replace('"', '').strip()
                    row[2] = row[2].replace('"', '').strip()
                    if row[0] != "":
                        sentFlag = False
                        sentence.append(row[2])
                        wordCounter += 1
                        if wordCounter < 7:
                            self.name[text].append(row[0])
                    else:
                        if sentFlag:
                            continue
                        sentFlag = True
                        length = len(sentence)
                        if length < 3:
                            sentence.clear()
                            continue
                        self.data[text].append([sentence[0], sentence[1], sentence[length - 3],
                                                sentence[length - 2], sentence[length - 1]])
                        sentCounter += 1
                        sentence.clear()

    def process_point_9(self):
        """Пункт 9: Анализ длин слов в отрывках."""
        finalTable9 = [['Текст', 'Кол.Отрыв', 'ср.длина', 'ср.дисп', 'ср.откл', 'отклонение', 'дисперсия', 'sd', 't']]
        result = []
        for text in range(self.COUNT):
            mass = []
            with open(f"{self.AUTHOR}_csv/{self.allText[text]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                counter = 0
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        mass.append(len(row[0]))
                    if counter == self.LENGTH:
                        result.append([text, np.mean(mass), np.var(mass), np.std(mass)])
                        mass.clear()
                        counter = 0

        coTRAIN = sum(1 for r in result if self.allText[r[0]] in self.trainText)
        meTRAIN = sum(r[1] for r in result if self.allText[r[0]] in self.trainText)
        vaTRAIN = sum(r[2] for r in result if self.allText[r[0]] in self.trainText)
        stTRAIN = sum(r[3] for r in result if self.allText[r[0]] in self.trainText)
        mTRAIN = meTRAIN / coTRAIN if coTRAIN > 0 else 0
        meanMassTrain = [r[1] for r in result if self.allText[r[0]] in self.trainText]
        sTRAIN = np.std(meanMassTrain) if coTRAIN > 1 else 0
        dTRAIN = np.var(meanMassTrain) if coTRAIN > 1 else 0
        finalTable9.append(['TRAIN', coTRAIN, mTRAIN, vaTRAIN / coTRAIN if coTRAIN > 0 else 0,
                            stTRAIN / coTRAIN if coTRAIN > 0 else 0, dTRAIN, sTRAIN])

        for currentText in range(self.COUNT):
            coTEST = sum(1 for r in result if r[0] == currentText)
            meTEST = sum(r[1] for r in result if r[0] == currentText)
            vaTEST = sum(r[2] for r in result if r[0] == currentText)
            stTEST = sum(r[3] for r in result if r[0] == currentText)
            mTEST = meTEST / coTEST if coTEST > 0 else 0
            meanMassTest = [r[1] for r in result if r[0] == currentText]
            sTEST = np.std(meanMassTest) if coTEST > 1 else 0
            dTEST = np.var(meanMassTest) if coTEST > 1 else 0
            sd = np.sqrt(
                ((coTRAIN - 1) * dTRAIN + (coTEST - 1) * dTEST) / (coTRAIN + coTEST - 2)) if coTRAIN + coTEST > 2 else 0
            answer = ((mTEST - mTRAIN) / sd * np.sqrt(coTRAIN * coTEST / (coTRAIN + coTEST))) if sd != 0 else 0
            finalTable9.append([f'#{currentText}', coTEST, mTEST, vaTEST / coTEST if coTEST > 0 else 0,
                                stTEST / coTEST if coTEST > 0 else 0, dTEST, sTEST, sd, answer])
        return finalTable9

    def process_point_10(self):
        """Пункт 10: Частоты слов различной длины."""
        result = []
        counter = [0] * self.COUNT
        for i in range(self.COUNT):
            wordLen = [i] + [0] * 16
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        counter[i] += 1
                        WL = len(row[0])
                        if WL < 16:
                            wordLen[WL] += 1
                        else:
                            wordLen[16] += 1
                result.append(wordLen)

        train = [0] * 16
        trainCounter = 0
        for i in range(len(result)):
            if self.allText[result[i][0]] in self.trainText:
                trainCounter += counter[i]
                for j in range(16):
                    train[j] += result[i][j + 1]
        p1 = [train[j] / trainCounter for j in range(16)]
        p1n = np.cumsum(p1)

        alpha10 = []
        for i in range(self.COUNT):
            p2 = [result[i][j + 1] / counter[i] for j in range(16)]
            p2n = np.cumsum(p2)
            d = [abs(p1n[j] - p2n[j]) for j in range(16)]
            alpha10.append(max(d) * np.sqrt(trainCounter * counter[i] / (trainCounter + counter[i])))
        return alpha10

    def process_point_11(self):
        """Пункт 11: Анализ длин предложений."""
        finalTable11 = [['Текст', 'Кол.Отрыв', 'ср.длина', 'ср.дисп', 'ср.откл', 'отклонение', 'дисперсия', 'sd', 't']]
        result = []
        for i in range(self.COUNT):
            mass = []
            wCounter = 0
            sCounter = 0
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                sflag = True
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        wCounter += 1
                        sflag = False
                    else:
                        if sflag:
                            continue
                        sflag = True
                        sCounter += 1
                        mass.append(wCounter)
                        wCounter = 0
                    if sCounter == self.SENT:
                        result.append([i, np.mean(mass), np.var(mass), np.std(mass)])
                        mass.clear()
                        sCounter = 0

        coTRAIN = sum(1 for r in result if self.allText[r[0]] in self.trainText)
        meTRAIN = sum(r[1] for r in result if self.allText[r[0]] in self.trainText)
        vaTRAIN = sum(r[2] for r in result if self.allText[r[0]] in self.trainText)
        stTRAIN = sum(r[3] for r in result if self.allText[r[0]] in self.trainText)
        mTRAIN = meTRAIN / coTRAIN if coTRAIN > 0 else 0
        meanMassTrain = [r[1] for r in result if self.allText[r[0]] in self.trainText]
        sTRAIN = np.std(meanMassTrain) if coTRAIN > 1 else 0
        dTRAIN = np.var(meanMassTrain) if coTRAIN > 1 else 0
        finalTable11.append(['TRAIN', coTRAIN, mTRAIN, vaTRAIN / coTRAIN if coTRAIN > 0 else 0,
                             stTRAIN / coTRAIN if coTRAIN > 0 else 0, dTRAIN, sTRAIN])

        for currentText in range(self.COUNT):
            coTEST = sum(1 for r in result if r[0] == currentText)
            meTEST = sum(r[1] for r in result if r[0] == currentText)
            vaTEST = sum(r[2] for r in result if r[0] == currentText)
            stTEST = sum(r[3] for r in result if r[0] == currentText)
            mTEST = meTEST / coTEST if coTEST > 0 else 0
            meanMassTest = [r[1] for r in result if r[0] == currentText]
            sTEST = np.std(meanMassTest) if coTEST > 1 else 0
            dTEST = np.var(meanMassTest) if coTEST > 1 else 0
            sd = np.sqrt(
                ((coTRAIN - 1) * dTRAIN + (coTEST - 1) * dTEST) / (coTRAIN + coTEST - 2)) if coTRAIN + coTEST > 2 else 0
            answer = ((mTEST - mTRAIN) / sd * np.sqrt(coTRAIN * coTEST / (coTRAIN + coTEST))) if sd != 0 else 0
            finalTable11.append([f'#{currentText}', coTEST, mTEST, vaTEST / coTEST if coTEST > 0 else 0,
                                 stTEST / coTEST if coTEST > 0 else 0, dTEST, sTEST, sd, answer])
        return finalTable11

    def process_point_12(self):
        """Пункт 12: Частоты длин предложений в интервалах по 5 слов."""
        fiveParts = 13
        f = [[0] * fiveParts for _ in range(self.COUNT)]
        sCounter = [0] * self.COUNT
        for i in range(self.COUNT):
            wCounter = 0
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                sflag = True
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        wCounter += 1
                        sflag = False
                    else:
                        if sflag:
                            continue
                        sflag = True
                        sCounter[i] += 1
                        if wCounter > 64:
                            wCounter = 64
                        f[i][math.ceil(wCounter / 5) - 1] += 1
                        wCounter = 0

        train = [0] * fiveParts
        trainCounter = 0
        for i in range(self.COUNT):
            if self.allText[i] in self.trainText:
                trainCounter += sCounter[i]
                for j in range(fiveParts):
                    train[j] += f[i][j]
        p1 = [train[j] / trainCounter for j in range(fiveParts)]
        p1n = np.cumsum(p1)

        alpha12 = []
        for i in range(self.COUNT):
            p2 = [f[i][j] / sCounter[i] for j in range(fiveParts)]
            p2n = np.cumsum(p2)
            d = [abs(p1n[j] - p2n[j]) for j in range(fiveParts)]
            alpha12.append(max(d) * np.sqrt(trainCounter * sCounter[i] / (trainCounter + sCounter[i])))
        return alpha12

    def process_point_13(self):
        """Пункт 13: Частоты встречаемости слов."""
        devi = 10
        spek = [[0] * devi for _ in range(self.COUNT)]
        partCounter = [0] * self.COUNT
        totalCounter = [0] * self.COUNT
        for i in range(self.COUNT):
            text = []
            counter = 0
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        text.append(row[0].lower())
                    if counter == self.LENGTH:
                        partCounter[i] += 1
                        yet = []
                        for word in text:
                            if word in yet:
                                continue
                            yet.append(word)
                            col = text.count(word)
                            if col > devi:
                                col = devi
                            spek[i][col - 1] += 1
                        counter = 0
                        text.clear()

        for i in range(self.COUNT):
            for j in range(devi):
                totalCounter[i] += spek[i][j]

        trainSpek = [0] * devi
        trainTotal = 0
        for i in range(self.COUNT):
            if self.allText[i] in self.trainText:
                for j in range(devi):
                    trainSpek[j] += spek[i][j]
                trainTotal += totalCounter[i]
        tp = [trainSpek[j] / trainTotal for j in range(devi)]
        tpn = np.cumsum(tp)

        ld13 = []
        for i in range(self.COUNT):
            p = [spek[i][j] / totalCounter[i] for j in range(devi)]
            pn = np.cumsum(p)
            d = [abs(tpn[j] - pn[j]) for j in range(devi)]
            ld13.append(max(d) * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i])))
        return ld13

    def process_point_14(self):
        """Пункт 14: Модифицированный анализ частот с весами."""
        devi = 10
        spek = [[0] * devi for _ in range(self.COUNT)]
        partCounter = [0] * self.COUNT
        totalCounter = [0] * self.COUNT
        for i in range(self.COUNT):
            text = []
            counter = 0
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        totalCounter[i] += 1
                        text.append(row[0].lower())
                    if counter == self.LENGTH:
                        partCounter[i] += 1
                        yet = []
                        for word in text:
                            if word in yet:
                                continue
                            yet.append(word)
                            col = text.count(word)
                            if col > devi:
                                col = devi
                            spek[i][col - 1] += 1
                        counter = 0
                        text.clear()

        mf = []
        for i in range(self.COUNT):
            mf.append([spek[i][j] * (j + 1) for j in range(devi - 1)])
            mfSum = sum(mf[i])
            mf[i].append(partCounter[i] * self.LENGTH - mfSum)

        trainSpek = [0] * devi
        trainTotal = 0
        for i in range(self.COUNT):
            if self.allText[i] in self.trainText:
                for j in range(devi):
                    trainSpek[j] += mf[i][j]
                trainTotal += partCounter[i] * self.LENGTH
        tp = [trainSpek[j] / trainTotal for j in range(devi)]
        tpn = np.cumsum(tp)

        ld14 = []
        for i in range(self.COUNT):
            totalCounter[i] = partCounter[i] * self.LENGTH
            p = [mf[i][j] / totalCounter[i] for j in range(devi)]
            pn = np.cumsum(p)
            d = [abs(tpn[j] - pn[j]) for j in range(devi)]
            ld14.append(max(d) * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i])))
        return ld14

    def process_point_15(self):
        """Пункт 15: Уникальные слова в отрывках."""
        partlen = []
        partlen0 = []
        for i in range(self.COUNT):
            mass = []
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                counter = 0
                for row in reader:
                    row[0] = row[0].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        if not row[0].lower() in mass:
                            mass.append(row[0].lower())
                    if counter == self.LENGTH:
                        if self.allText[i] in self.trainText:
                            partlen0.append(len(mass))
                        partlen.append([i, len(mass)])
                        mass.clear()
                        counter = 0

        mean0 = np.mean(partlen0) if partlen0 else 0
        var0 = np.var(partlen0) if len(partlen0) > 1 else 0
        n0 = len(partlen0)

        res15 = []
        for i in range(self.COUNT):
            partlen1 = [p[1] for p in partlen if p[0] == i]
            mean1 = np.mean(partlen1) if partlen1 else 0
            var1 = np.var(partlen1) if len(partlen1) > 1 else 0
            n1 = len(partlen1)
            sd = np.sqrt(((n0 - 1) * var0 + (n1 - 1) * var1) / (n1 + n0 - 2)) if n1 + n0 > 2 else 0
            answer = ((mean1 - mean0) / sd * np.sqrt(n1 * n0 / (n0 + n1))) if sd != 0 else 0
            res15.append([i, n1, mean1, var1, sd, answer])
        return res15

    def process_point_13mod(self):
        """Пункт 13mod: Частоты с начальной формой слов."""
        devi = 10
        spek = [[0] * devi for _ in range(self.COUNT)]
        partCounter = [0] * self.COUNT
        totalCounter = [0] * self.COUNT
        for i in range(self.COUNT):
            text = []
            counter = 0
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                for row in reader:
                    row[1] = row[1].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        text.append(row[1].lower())
                    if counter == self.LENGTH:
                        partCounter[i] += 1
                        yet = []
                        for word in text:
                            if word in yet:
                                continue
                            yet.append(word)
                            col = text.count(word)
                            if col > devi:
                                col = devi
                            spek[i][col - 1] += 1
                        counter = 0
                        text.clear()

        for i in range(self.COUNT):
            for j in range(devi):
                totalCounter[i] += spek[i][j]

        trainSpek = [0] * devi
        trainTotal = 0
        for i in range(self.COUNT):
            if self.allText[i] in self.trainText:
                for j in range(devi):
                    trainSpek[j] += spek[i][j]
                trainTotal += totalCounter[i]
        tp = [trainSpek[j] / trainTotal for j in range(devi)]
        tpn = np.cumsum(tp)

        ld13m = []
        for i in range(self.COUNT):
            p = [spek[i][j] / totalCounter[i] for j in range(devi)]
            pn = np.cumsum(p)
            d = [abs(tpn[j] - pn[j]) for j in range(devi)]
            ld13m.append(max(d) * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i])))
        return ld13m

    def process_point_14mod(self):
        """Пункт 14mod: Модифицированный анализ с начальной формой слов."""
        devi = 10
        spek = [[0] * devi for _ in range(self.COUNT)]
        partCounter = [0] * self.COUNT
        totalCounter = [0] * self.COUNT
        for i in range(self.COUNT):
            text = []
            counter = 0
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                for row in reader:
                    row[1] = row[1].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        totalCounter[i] += 1
                        text.append(row[1].lower())
                    if counter == self.LENGTH:
                        partCounter[i] += 1
                        yet = []
                        for word in text:
                            if word in yet:
                                continue
                            yet.append(word)
                            col = text.count(word)
                            if col > devi:
                                col = devi
                            spek[i][col - 1] += 1
                        counter = 0
                        text.clear()

        mf = []
        for i in range(self.COUNT):
            mf.append([spek[i][j] * (j + 1) for j in range(devi - 1)])
            mfSum = sum(mf[i])
            mf[i].append(partCounter[i] * self.LENGTH - mfSum)

        trainSpek = [0] * devi
        trainTotal = 0
        for i in range(self.COUNT):
            if self.allText[i] in self.trainText:
                for j in range(devi):
                    trainSpek[j] += mf[i][j]
                trainTotal += partCounter[i] * self.LENGTH
        tp = [trainSpek[j] / trainTotal for j in range(devi)]
        tpn = np.cumsum(tp)

        ld14m = []
        for i in range(self.COUNT):
            totalCounter[i] = partCounter[i] * self.LENGTH
            p = [mf[i][j] / totalCounter[i] for j in range(devi)]
            pn = np.cumsum(p)
            d = [abs(tpn[j] - pn[j]) for j in range(devi)]
            ld14m.append(max(d) * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i])))
        return ld14m

    def process_point_15mod(self):
        """Пункт 15mod: Уникальные начальные формы слов."""
        partlen = []
        partlen0 = []
        for i in range(self.COUNT):
            mass = []
            with open(f"{self.AUTHOR}_csv/{self.allText[i]}.csv", encoding='UTF-8', newline='') as File:
                reader = csv.reader(File, delimiter=',', quotechar=',', quoting=csv.QUOTE_NONE)
                counter = 0
                for row in reader:
                    row[1] = row[1].replace('"', '').strip()
                    if row[0] != "":
                        counter += 1
                        if not row[1].lower() in mass:
                            mass.append(row[1].lower())
                    if counter == self.LENGTH:
                        if self.allText[i] in self.trainText:
                            partlen0.append(len(mass))
                        partlen.append([i, len(mass)])
                        mass.clear()
                        counter = 0

        mean0 = np.mean(partlen0) if partlen0 else 0
        var0 = np.var(partlen0) if len(partlen0) > 1 else 0
        n0 = len(partlen0)

        res15m = []
        for i in range(self.COUNT):
            partlen1 = [p[1] for p in partlen if p[0] == i]
            mean1 = np.mean(partlen1) if partlen1 else 0
            var1 = np.var(partlen1) if len(partlen1) > 1 else 0
            n1 = len(partlen1)
            sd = np.sqrt(((n0 - 1) * var0 + (n1 - 1) * var1) / (n1 + n0 - 2)) if n1 + n0 > 2 else 0
            answer = ((mean1 - mean0) / sd * np.sqrt(n1 * n0 / (n0 + n1))) if sd != 0 else 0
            res15m.append([i, n1, mean1, var1, sd, answer])
        return res15m

    def write_to_excel(self, finalTable9, alpha10, finalTable11, alpha12, ld13, ld14, res15, ld13m, ld14m, res15m):
        """Запись результатов в Excel."""
        workbook = xlsxwriter.Workbook(self.xlsxNAME)
        worksheet = workbook.add_worksheet()
        trainFormat = workbook.add_format({'fg_color': 'green'})
        badFormat = workbook.add_format({'fg_color': 'red'})
        borderFormat = workbook.add_format({'fg_color': 'silver'})
        worksheet.write(0, 0, 'Код', borderFormat)
        maxs = [0] * 18
        for text in range(self.COUNT):
            worksheet.write(0, text + 1, text + 1, borderFormat)
            if self.allText[text] in self.trainText:
                if abs(finalTable9[text + 2][8]) > abs(maxs[1]):
                    maxs[1] = abs(finalTable9[text + 2][8])
                if abs(alpha10[text]) > abs(maxs[2]):
                    maxs[2] = abs(alpha10[text])
                if abs(finalTable11[text + 2][8]) > abs(maxs[3]):
                    maxs[3] = abs(finalTable11[text + 2][8])
                if abs(alpha12[text]) > abs(maxs[4]):
                    maxs[4] = abs(alpha12[text])
                if abs(ld13[text]) > abs(maxs[5]):
                    maxs[5] = abs(ld13[text])
                if abs(ld14[text]) > abs(maxs[6]):
                    maxs[6] = abs(ld14[text])
                if abs(res15[text][5]) > abs(maxs[7]):
                    maxs[7] = abs(res15[text][5])
                if abs(ld13m[text]) > abs(maxs[8]):
                    maxs[8] = abs(ld13m[text])
                if abs(ld14m[text]) > abs(maxs[9]):
                    maxs[9] = abs(ld14m[text])
                if abs(res15m[text][5]) > abs(maxs[10]):
                    maxs[10] = abs(res15m[text][5])

        for xlRow in range(self.COUNT):
            if self.allText[xlRow] in self.trainText:
                worksheet.write(xlRow + 1, 0, self.allText[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 1, finalTable9[xlRow + 2][8], trainFormat)
                worksheet.write(xlRow + 1, 2, alpha10[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 3, finalTable11[xlRow + 2][8], trainFormat)
                worksheet.write(xlRow + 1, 4, alpha12[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 5, ld13[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 6, ld14[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 7, res15[xlRow][5], trainFormat)
                worksheet.write(xlRow + 1, 8, ld13m[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 9, ld14m[xlRow], trainFormat)
                worksheet.write(xlRow + 1, 10, res15m[xlRow][5], trainFormat)
                strName = str(self.name[xlRow]).strip('[]')
                worksheet.write(xlRow + 1, 11, strName.replace(',', '').replace('\'', ''), trainFormat)
            else:
                worksheet.write(xlRow + 1, 0, self.allText[xlRow])
                if abs(finalTable9[xlRow + 2][8]) > maxs[1]:
                    worksheet.write(xlRow + 1, 1, finalTable9[xlRow + 2][8], badFormat)
                else:
                    worksheet.write(xlRow + 1, 1, finalTable9[xlRow + 2][8])
                if abs(alpha10[xlRow]) > maxs[2]:
                    worksheet.write(xlRow + 1, 2, alpha10[xlRow], badFormat)
                else:
                    worksheet.write(xlRow + 1, 2, alpha10[xlRow])
                if abs(finalTable11[xlRow + 2][8]) > maxs[3]:
                    worksheet.write(xlRow + 1, 3, finalTable11[xlRow + 2][8], badFormat)
                else:
                    worksheet.write(xlRow + 1, 3, finalTable11[xlRow + 2][8])
                if abs(alpha12[xlRow]) > maxs[4]:
                    worksheet.write(xlRow + 1, 4, alpha12[xlRow], badFormat)
                else:
                    worksheet.write(xlRow + 1, 4, alpha12[xlRow])
                if abs(ld13[xlRow]) > maxs[5]:
                    worksheet.write(xlRow + 1, 5, ld13[xlRow], badFormat)
                else:
                    worksheet.write(xlRow + 1, 5, ld13[xlRow])
                if abs(ld14[xlRow]) > maxs[6]:
                    worksheet.write(xlRow + 1, 6, ld14[xlRow], badFormat)
                else:
                    worksheet.write(xlRow + 1, 6, ld14[xlRow])
                if abs(res15[xlRow][5]) > maxs[7]:
                    worksheet.write(xlRow + 1, 7, res15[xlRow][5], badFormat)
                else:
                    worksheet.write(xlRow + 1, 7, res15[xlRow][5])
                if abs(ld13m[xlRow]) > maxs[8]:
                    worksheet.write(xlRow + 1, 8, ld13m[xlRow], badFormat)
                else:
                    worksheet.write(xlRow + 1, 8, ld13m[xlRow])
                if abs(ld14m[xlRow]) > maxs[9]:
                    worksheet.write(xlRow + 1, 9, ld14m[xlRow], badFormat)
                else:
                    worksheet.write(xlRow + 1, 9, ld14m[xlRow])
                if abs(res15m[xlRow][5]) > maxs[10]:
                    worksheet.write(xlRow + 1, 10, res15m[xlRow][5], badFormat)
                else:
                    worksheet.write(xlRow + 1, 10, res15m[xlRow][5])
                strName = str(self.name[xlRow]).strip('[]')
                worksheet.write(xlRow + 1, 11, strName.replace(',', '').replace('\'', ''))
        workbook.close()


if __name__ == "__main__":
    hetco_utils = HetcoUtils()
    hetco_utils.read_data()
    finalTable9 = hetco_utils.process_point_9()
    alpha10 = hetco_utils.process_point_10()
    finalTable11 = hetco_utils.process_point_11()
    alpha12 = hetco_utils.process_point_12()
    ld13 = hetco_utils.process_point_13()
    ld14 = hetco_utils.process_point_14()
    res15 = hetco_utils.process_point_15()
    ld13m = hetco_utils.process_point_13mod()
    ld14m = hetco_utils.process_point_14mod()
    res15m = hetco_utils.process_point_15mod()
    hetco_utils.write_to_excel(finalTable9, alpha10, finalTable11, alpha12, ld13, ld14, res15, ld13m, ld14m, res15m)
