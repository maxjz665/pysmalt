function showProperty(e, content, useOldType) {
    //alert(JSON.stringify(content));
    if (prevPopover)
        prevPopover.popover('hide');

    $(e).popover({
        content: prepareContent(content, useOldType),
        container: 'body',
        title: "<span>Атрибуты слова</span><button class=\"btn btn-primary btn-sm\" style=\"float:right; position:relative; top:-5px;\" onclick='prevPopover.popover(&quot;hide&quot;);'>&times;</button>",
        html: true,
        sanitize: false
    });
    prevPopover = $(e);
    prevPopover.popover('show');
    console.log(content);
}

var prevPopover = null;

function prepareContent(content, useOldType) {
    ret = "<b>Слово в тексте:</b> " + content.WORD + (content.level > 0 ?
        "<a type='button' class='btn btn-primary btn-sm' href='?action=edit-word&text=" + content.TEXT_ID +
            "&chapter=" + content.CHAPTER_INDEX +
            "&paragraph=" + content.PARAGRAPH_INDEX +
            "&sentence=" + content.SENTENCE_INDEX +
            "&word=" + content.WORD_INDEX +
            (useOldType ? "&type=old" : "&type=new") + "'>Редактировать слово</a><br/>" : "<br/>");
    if (content.ID) {
        ret += "<b>Слово разбора:</b> " + content.WORD_01 + (content.level ? " (id=" + content.ID + ")</br>" : "</br>") +
            (content.level > 0 ? "<a type='button' class='btn btn-primary btn-sm' href='?action=add-entity&wordId=" + content.ID_WORD +
                "&textId=" + content.TEXT_ID +
                (useOldType ? "&type=old" : "&type=new") + "'>Создать разбор</a><br/>" : "") +
            "<b>Начальная форма:</b> " + content.INITIAL_FORM + "</br>" +
            "<b>Современное написание:</b> " + content.MODERN  +
            (content.INIT_MODERN ? "</br> <b>Современное написание начальной формы:</b> " + content.INIT_MODERN : "");
        if (content.FOUND_PARAM_COUNT) {
            ret += "</br>" +
                "<b>Количество параметров:</b> " + content.PARAMS_COUNT + "</br>" +
                "<b>Количество найденных параметров:</b>" + content.FOUND_PARAM_COUNT;
            ret += "<ul>" + parseArray(content[0]) + "</ul>";
        } else {
            ret += parseArray(content[0], false);
        }
    } else {
        ret += "<b>НЕТ РАЗБОРА!</b><br/>" +
            "<a type='button' class='btn btn-primary btn-sm' href='?action=add-entity&wordId=" + content.ID_WORD +
            "&textId=" + content.TEXT_ID +
            (useOldType ? "&type=old" : "&type=new") + "'>Добавить разбор</a><br/>";
    }

    console.log(ret);
    return ret;
}

function parseArray(arr, useul=true) {
    ret = "";
    if (useul) {
        delim = "<li>";
    } else {
        delim = "<br/>";
    }
    console.log(Array.isArray(arr));
    if (Array.isArray(arr))
        arr.forEach(function (item, i, arr) {
            if (Array.isArray(item) && item.length > 0) {
                if (item.length > 1)
                    ret += "<ul style='padding: 5px'>" + parseArray(item) + "</ul>";
                else
                    ret += parseArray(item);
            } else {
                if (item.error) {
                    ret += delim + "<b>" + item.name + "</b>: <div style='color: red;'>Ошибка разбора значения параметра (" + item.index + "): текущее значение=" + item.offset + ", допустимое максимальное значение=" + item.count + "</div>";
                } else if (item.name)
                    ret += delim + "<b>" + item.name + "</b>: " + item.value;
            }
        });

    return ret;
}

function updateAttrView(event, usedType) {
    event.preventDefault();
    let request = {};
    for (let i = 1; i <= 20; i++) {
        let param_name = 'PARAM_' + (i < 10 ? '0' : '') + i;
        request[param_name] = document.getElementById(param_name + '-input').value;
    }
    console.log(usedType);
    $.ajax({
        url: "attrs.php",
        type: "POST",
        data: {params: request, type: usedType, action: "print"},
        success: function (result) {
            console.log(result);
            document.getElementById('attr-view').innerHTML =
                "<b> Количество найденных параметров: </b>" + result.FOUND_PARAM_COUNT + "<br/>" +
                "<ul>" + parseArray(result[0]) + "</ul>";
        },
        error: function (msg) {
            document.getElementById('attr-view').innerHTML = JSON.stringify(msg);
        }
    });
}

function showPossibleValues(event, position, usedType) {
    console.log("Show help for position " + position);
    event.preventDefault();


    let request = {};
    for (let i = 1; i <= 20; i++) {
        let param_name = 'PARAM_' + (i < 10 ? '0' : '') + i;
        request[param_name] = document.getElementById(param_name + '-input').value;
    }

    let modal = $('#paramHelper');
    modal.find(".modal-title").text("Варианты значений параметра " + position);
    modal.modal('show');
    $.ajax({
        url: "attrs.php",
        type: "POST",
        data: {params: request, type: usedType, position, action: "help"},
        success: function (result) {
            console.log(result);
            modal.find(".modal-body").html(printAttributes(result));
        },
        error: function (msg) {
            modal.find(".modal-body").html(JSON.stringify(msg));
        }
    })
}

function getSentenceListForWord(event, entryId, usedType, placeholder='#sentence-list') {
    let sentence = $(placeholder);
    sentence.html("<div class='wait'>Wait...</div>");
    event.preventDefault();
    $.ajax({
        url: "attrs.php",
        type: "POST",
        data: {action: "sentence", entry: entryId, type: usedType},
        success: function (result) {
            sentence.html("<div class=\"alert alert-info alert-dismissible fade show\" role=\"alert\"><h2>Контекст</h2><ul>" + result + "</ul><button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        },
        error: function (msg) {
            console.log(msg);
        }
    });
}

function getTextListForAuthor(event, entryId, placeholder='#sentence-list') {
    let sentence = $(placeholder);
    sentence.html("<div class='wait'>Wait...</div>");
    event.preventDefault();
    $.ajax({
        url: "index.php",
        type: "POST",
        data: {action: "author-text-list", entry: entryId},
        success: function (result) {
            sentence.html("<div class=\"alert alert-info alert-dismissible fade show\" role=\"alert\"><h2>Тексты</h2><ul>" + result + "</ul><button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        },
        error: function (msg) {
            console.log(msg);
        }
    });
}

function insertAuthor(event) {
    event.preventDefault();
    let name = document.getElementById('name[new]').value;
    let origin_name = document.getElementById('origin_name[new]').value;
    let real_name = document.getElementById('real_name[new]').value;

    $.ajax({
        url: "updatedb.php",
        type: 'POST',
        data: {name, origin_name, real_name, action: "add-author"},
        success: function (result) {
            console.log(result);
            window.location.reload();
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("author[new]-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");

        }
    });

}

function updateAuthor(event, id) {
    event.preventDefault();

    let name = document.getElementById("name[" + id + "]").value;
    let origin_name = document.getElementById("origin_name[" + id + "]").value;
    let real_name = document.getElementById("real_name[" + id + "]").value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, name, origin_name, real_name, action: "update-author"},
        success: function (result) {
            console.log(result);
            document.getElementById("author[" + id + "]-msg-view").innerHTML = result;
            markCard(id, false);
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("author[" + id + "]-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });

}

function deleteAuthor(event, entryId, placeholder= '#entry-list', errorplace='entry-error-msg') {
    let place = $(placeholder);
    place.html("<div class='wait'>Wait...</div>");
    event.preventDefault();
    $.ajax({
        url: "updatedb.php",
        type: "post",
        data: {action: "remove-author", entry: entryId},
        success: function () {
            window.location.reload(false);
        },
        error: function (msg) {
            place.html( msg.responseText);
        }
    });
}

function getTextListForMagazine(event, entryId, placeholder='#sentence-list') {
    let sentence = $(placeholder);
    sentence.html("<div class='wait'>Wait...</div>");
    event.preventDefault();
    $.ajax({
        url: "index.php",
        type: "POST",
        data: {action: "magazine-text-list", entry: entryId},
        success: function (result) {
            sentence.html("<div class=\"alert alert-info alert-dismissible fade show\" role=\"alert\"><h2>Тексты</h2><ul>" + result + "</ul><button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        },
        error: function (msg) {
            console.log(msg);
        }
    });
}

function insertMagazine(event) {
    event.preventDefault();
    let title = document.getElementById('name[new]').value;
    let origin_title = document.getElementById('origin_name[new]').value;

    $.ajax({
        url: "updatedb.php",
        type: 'POST',
        data: {title, origin_title, action: "add-magazine"},
        success: function (result) {
            console.log(result);
            window.location.reload();
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("magazine[new]-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");

        }
    });

}

function updateMagazine(event, id) {
    event.preventDefault();

    let title = document.getElementById("name[" + id + "]").value;
    let origin_title = document.getElementById("origin_name[" + id + "]").value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, title, origin_title, action: "update-magazine"},
        success: function (result) {
            console.log(result);
            document.getElementById("magazine[" + id + "]-msg-view").innerHTML = result;
            markCard(id, false);
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("magazine[" + id + "]-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });

}

function deleteMagazine(event, entryId, placeholder= '#entry-list', errorplace='entry-error-msg') {
    let place = $(placeholder);
    place.html("<div class='wait'>Wait...</div>");
    event.preventDefault();
    $.ajax({
        url: "updatedb.php",
        type: "post",
        data: {action: "remove-magazine", entry: entryId},
        success: function () {
            window.location.reload(false);
        },
        error: function (msg) {
            place.html( msg.responseText);
        }
    });
}

function printAttributes(result) {
    if (!result)
        return "<b>Параметр не допускается</b>";
    let ret = "<b>Название:</b> " + result.name + " (" + result.paramId + "), index=" + result.idx;
    if (result.params && result.params.length > 0) {
        ret += "<ul>";
        result.params.map((v) => {
            ret += (v.param === result.paramId ? "<li><b>" + v.name + " (" + v.param + ")</b>" : "<li>" + v.name + " (" + v.param + ")");
        });
        ret += "</ul>";
    } else {
        ret += "<br/>";
    }
    ret += "<b>Родительский параметр:</b> " + result.prevParamId + " (индекс=" + result.prevIdx + ")<br/>";
    ret += "<b>Варианты значений:</b> <ul>";
    if (result.values && result.values.length > 0) {
        result.values.map((v) => {
            ret += "<li>" + v.position + ": " + v.name + " (" + v.value + ")</li>";
        });
    } else {
        ret += "Нет вариантов!!!";
    }
    ret += "</ul>";

    //ret += JSON.stringify(result);

    return ret;
}

let isSpaceShowed = false;

let showedWordTypeID = -1;

function showWordsWithSpace() {
    if (showedWordTypeID !== -1) {
        $(".word-type-" + showedWordTypeID).toggleClass("show-blue");
        showedWordTypeID = -1;
    }

    $(".word-hasspace").toggleClass("show-blue");
}

function showWordsWithType() {
    var e = $("#word-type").children("option:selected").val();
    if (e !== showedWordTypeID && showedWordTypeID !== -1) {
        $(".word-type-" + showedWordTypeID).toggleClass("show-blue");
    }
    if (isSpaceShowed)
        showWordsWithSpace();

    showedWordTypeID = e;
    console.log(".word-type-" + showedWordTypeID);
    $(`.word-type-${showedWordTypeID}`).toggleClass("show-blue");
}

function showWordErrors() {
    $(".word-mark").toggleClass("word-mark-val");
    $(".word-redmark").toggleClass("word-redmark-val");
}

function updateEntry(event, usedType, id) {
    event.preventDefault();

    let request = {};
    for (let i = 1; i <= 20; i++) {
        let param_name = 'PARAM_' + (i < 10 ? '0' : '') + i;
        request[param_name] = document.getElementById(param_name + '-input').value;
    }
    let word = document.getElementById("word-input").value;
    let init_form = document.getElementById('word-init-form-input').value;
    let modern = document.getElementById('word-modern-input').value;
    let init_modern = document.getElementById('word-init-modern-input').value;
    let params_count = document.getElementById('attr-count-input').value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {params: request, type: usedType, action: "save-entry", word, init_form, modern, init_modern, params_count, id},
        success: function (result) {
            console.log(result);
            document.getElementById('msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('msg-view').innerHTML = msg.responseText;
        }
    });

}

function createEntry(event, usedType, textId, wordId) {
    event.preventDefault();

    let request = {};
    for (let i = 1; i <= 20; i++) {
        let param_name = 'PARAM_' + (i < 10 ? '0' : '') + i;
        request[param_name] = document.getElementById(param_name + '-input').value;
    }
    let word = document.getElementById("word-input").value;
    let init_form = document.getElementById('word-init-form-input').value;
    let modern = document.getElementById('word-modern-input').value;
    let init_modern = document.getElementById('word-init-modern-input').value;
    let params_count = document.getElementById('attr-count-input').value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {params: request, type: usedType, action: "create-entry", word, init_form, modern, init_modern, params_count, textId, wordId},
        success: function (result) {
            console.log(result);
            document.getElementById('msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('msg-view').innerHTML = msg.responseText;
        }
    });

}

function createNewEntry(event, usedType, id) {
    event.preventDefault();

    let request = {};
    for (let i = 1; i <= 20; i++) {
        let param_name = 'PARAM_' + (i < 10 ? '0' : '') + i;
        request[param_name] = document.getElementById(param_name + '-input').value;
    }
    let word = document.getElementById("word-input").value;
    let init_form = document.getElementById('word-init-form-input').value;
    let modern = document.getElementById('word-modern-input').value;
    let init_modern = document.getElementById('word-init-modern-input').value;
    let params_count = document.getElementById('attr-count-input').value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {params: request, type: usedType, action: "create-new-entry", word, init_form, modern, init_modern, params_count, id},
        success: function (result) {
            console.log(result);
            document.getElementById('msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('msg-view').innerHTML = msg.responseText;
        }
    });

}


function updateWordWriting(event, id) {
    event.preventDefault();

    let wordWriting = document.getElementById("word-input").value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, value: wordWriting, action: "save-word-writing"},
        success: function (result) {
            console.log(result);
            document.getElementById('word-writing-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('word-writing-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function updatePaper(event, id) {
    event.preventDefault();

    let TEXT_TYPE = document.getElementById('textType').value;
    let AUTHOR_VERIFY = document.getElementById('authorVerify').value;
    let CATEGORY = document.getElementById('category').value;
    let STATUS = document.getElementById('status').value;
    let AUTHOR_TYPE = document.getElementById('authorType').value;
    let AUTHOR_ID = document.getElementById('inputAuthor').value;
    let AUTHOR2_TYPE = document.getElementById('author2Type').value;
    let AUTHOR2_ID = document.getElementById('inputAuthor2').value;
    let AUTHOR3_TYPE = document.getElementById('author3Type').value;
    let AUTHOR3_ID = document.getElementById('inputAuthor3').value;
    let TITLE = document.getElementById('inputName').value;
    let ORIGIN_TITLE = document.getElementById('originTitle').value;
    let SHORT_TITLE = document.getElementById('shortTitle').value;
    let MAGAZINE_ID = document.getElementById('inputJournal').value;
    let MAGAZINE_NO = document.getElementById('inputJournalNo').value;
    let MAGAZINE_VOLUME = document.getElementById('magazineVolume').value;
    let MAGAZINE_SECTION = document.getElementById('magazineSection').value;
    let PUBLICATION_DATE = document.getElementById('inputDate').value;
    let PAGES = document.getElementById('pages').value;
    let CENSORSHIP = document.getElementById('censorship').value;
    let URL = document.getElementById('inputUrl').value;
    let COMMENT = document.getElementById('comment').value;
    let ATTRIBUTIONS = document.getElementById('attributions').value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, TEXT_TYPE, AUTHOR_VERIFY, CATEGORY, STATUS, AUTHOR_TYPE, AUTHOR_ID, AUTHOR2_TYPE, AUTHOR2_ID,
            AUTHOR3_TYPE, AUTHOR3_ID, TITLE, ORIGIN_TITLE, SHORT_TITLE, MAGAZINE_ID, MAGAZINE_NO, MAGAZINE_VOLUME,
            MAGAZINE_SECTION, PUBLICATION_DATE, PAGES, CENSORSHIP, URL, COMMENT, ATTRIBUTIONS, action: "update-paper"},
        success: function (result) {
            console.log(result);
            document.getElementById('update-paper-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('update-paper-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });

}

function saveWordParsing(event, id, usedType) {
    event.preventDefault();

    let parent = document.getElementById("wordParsingCard");

    if (parent.getElementsByClassName("list-group-item active").length === 0)
        return;

    let selectedItem = parent.getElementsByClassName("list-group-item active")[0].getAttribute("property");
    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, value: selectedItem, action: "change-word-parsing", usedType},
        success: function (result) {
            console.log(result);
            document.getElementById('word-parsing-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('word-parsing-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function makeCitation(event, id, citationType, usedType) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, value: citationType, action: "change-word-citation", usedType},
        success: function (result) {
            console.log(result);
            document.getElementById('word-parsing-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('word-parsing-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function sliceWord(event, id) {
    event.preventDefault();

    let firstWord = document.getElementById("slice-first-word-input").value;
    let secondWord = document.getElementById('slice-second-word-input').value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, firstWord, secondWord, action: "slice-word"},
        success: function (result) {
            console.log(result);
            document.getElementById('slice-word-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('slice-word-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    })
}

function deleteWord(event, id) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, action: "delete-word"},
        success: function (result) {
            console.log(result);
            document.getElementById('delete-word-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('delete-word-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    })
}

function deleteSentence(event, id) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, action: "delete-sentence"},
        success: function (result) {
            console.log(result);
            document.getElementById('delete-sentence-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('delete-sentence-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    })
}

function divideSentence(event, id) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, action: "divide-sentence"},
        success: function (result) {
            console.log(result);
            document.getElementById('divide-sentence-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('divide-sentence-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function divideSection(event, id) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, action: "divide-section"},
        success: function (result) {
            console.log(result);
            document.getElementById('divide-sentence-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('divide-sentence-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function mergeLeft(event, id) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, action: "merge-sentence-left"},
        success: function (result) {
            console.log(result);
            document.getElementById('merge-sentence-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('merge-sentence-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    })
}

function mergeRight(event, id) {
    event.preventDefault();

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, action: "merge-sentence-right"},
        success: function (result) {
            console.log(result);
            document.getElementById('merge-sentence-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('merge-sentence-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    })
}

function insertSentences(event, id) {
    event.preventDefault();

    let text = document.getElementById("text-fragment").value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, text, action: "insert-sentences"},
        success: function (result) {
            console.log(result);
            document.getElementById('insert-text-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('insert-text-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function insertSections(event, id) {
    event.preventDefault();

    let text = document.getElementById("text-fragment").value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, text, action: "insert-sections"},
        success: function (result) {
            console.log(result);
            document.getElementById('insert-text-msg-view').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('insert-text-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function enableEditMode() {
    console.log("BINGO");
    $(".editItem").toggleClass('showed-edit-item');
}

function removePaperFromList(e, id, oldValue) {
    e.preventDefault();

    console.log("Try to remove " + id + " with value=" + oldValue);

    let value = oldValue ? 0 : 1;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, value, action: "hide-paper"},
        success: function (result) {
            console.log(result);
            window.location.reload();
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('edit-msg-view').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });

    return false;
}

function updateWord(event, id, useOldType) {
    event.preventDefault();

    let initial = document.getElementById("initial[" + id + "]").value;
    let modern = document.getElementById("modern[" + id + "]").value;
    let init_modern = useOldType ? null : document.getElementById("init_modern[" + id + "]").value;

    $.ajax({
        url: "updatedb.php",
        type: "POST",
        data: {id, type: (useOldType ? "old" : "new"),  initial, modern, init_modern, action: "update-entry-writing"},
        success: function (result) {
            console.log(result);
            document.getElementById("word[" + id + "]-msg-view").innerHTML = result;
            markCard(id, false);
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("word[" + id + "]-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function markCard(id, isMark) {
    let nnode = $('#card\\[' + id + '\\]');
    if (isMark !== nnode.hasClass("bg-danger"))
        nnode.toggleClass("bg-danger");
}

function convertWordToLowerCase(event, id, word, placeSuccessHolder, placeErrorHolder) {
    event.preventDefault();
    $.ajax({
        url: "index.php",
        type: "POST",
        data: {word, action: "convert-to-lowercase"},
        success: function (result) {
            let place = $(placeSuccessHolder);
            place.val(result);
            markCard(id, true);
        },
        error: function (msg) {
            document.getElementById(placeErrorHolder).innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    })
}

function showTextarea(el) {
    if(el.checked === true) {
        document.getElementById('hiddenRow').style.display = 'block';
    }
    else if (el.checked === false){
        document.getElementById('hiddenRow').style.display = 'none';
    }
}

function showTextSelects(el) {
    if(el.checked === true) {
        document.getElementById('hiddenRow').style.display = 'none';
        if ( $('#baseTextNumber').length ){
            $('#baseTextNumber').prop('selectedIndex',0).selectpicker('refresh')
        }
        if ( $('#otherTextNumber').length ){
            $('#otherTextNumber').prop('selectedIndex',0).selectpicker('refresh')
        }
    }
    else if (el.checked === false){
        let a = $('#baseTextlistId');
        let b = $('#otherTextlistId');
        if (a.val() != null && b.val() == null && document.getElementById('hiddenRow').style.display === 'none') {
            document.getElementById('hiddenRow').style.display = 'flex';
            selectChanged('baseTextlistId', a.val());
        }
        if (b.val() != null && a.val() == null &&  document.getElementById('hiddenRow').style.display === 'none') {
            document.getElementById('hiddenRow').style.display = 'flex';
            selectChanged('otherTextlistId', b.val());
        }
        if(b.val() != null && b.val() != null &&  document.getElementById('hiddenRow').style.display === 'none') {
            document.getElementById('hiddenRow').style.display = 'flex';
            selectChanged('otherTextlistId', b.val());
            selectChanged('baseTextlistId', a.val());
        }
    }
}

function selectChanged(name, value) {
    if(document.getElementById("randomTexts").checked) return;
    let listId = value;
    document.getElementById('hiddenRow').style.display = 'flex'
    $.ajax({
        url: "text-generator.php",
        type: "POST",
        data: {showSelect: name, listId},
        success: function (result) {
            if(name === "otherTextlistId") {
                $('div[id="selectContainer2"]').html(result);
                $('#otherTextNumber').selectpicker('refresh')
            }
            if(name === "baseTextlistId") {
                $('div[id="selectContainer1"]').html(result);
                $('#baseTextNumber').selectpicker('refresh')
            }
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("selectionText").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}


function showTextGeneration(event, action, mode) {
    event.preventDefault();

    let baseTextlistId = document.getElementById('baseTextlistId').value;
    let otherTextlistId = document.getElementById('otherTextlistId').value;
    let codeCount = document.getElementById('codeCount').value;
    let percentOfInserts = document.getElementById('percentOfInserts').value;
    let fragmentSize = document.getElementById('fragmentSize').value;
    let bindBorders = document.getElementById('bindBorders').checked;
    let randomTexts = document.getElementById('randomTexts').checked;
    let baseTextNumber = null;
    let otherTextNumber = null;
    if(!randomTexts) {
        baseTextNumber = document.getElementById('baseTextNumber').value;
        otherTextNumber = document.getElementById('otherTextNumber').value;
    }
    // покажем спиннер
    document.getElementById("selectionText").innerHTML = "<div class=\"spinner-border  m-5\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";
    $.ajax({
        url: "text-generator.php",
        type: "POST",
        data: {mode, baseTextlistId, otherTextlistId, codeCount, percentOfInserts, fragmentSize, bindBorders, randomTexts, baseTextNumber, otherTextNumber, action: action},
        success: function (result) {
            //console.log(result);
            document.getElementById("selectionText").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("selectionText").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function showTextGenerationByCode(event, action, mode) {
    event.preventDefault();

    let code = document.getElementById('codeInput').value;
    // покажем спиннер
    document.getElementById("selectionText").innerHTML = "<div class=\"spinner-border  m-5\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";
    $.ajax({
        url: "text-generator.php",
        type: "POST",
        data: {mode, code, action: action},
        success: function (result) {
            //console.log(result);
            document.getElementById("selectionText").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("selectionText").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function copyAllCodesToClipboard(elementName) {

    var elements = document.getElementsByClassName("codeToCopy");

    var tempItem = document.createElement('input');

    tempItem.setAttribute('type','text');
    tempItem.setAttribute('display','none');

    let content = "";

    for (let i = 0; i < elements.length; i += 1) {
        if (elements[i] instanceof HTMLElement) {
            content += elements[i].innerHTML + ";"
        }
    }

    tempItem.setAttribute('value',content);
    document.body.appendChild(tempItem);

    tempItem.select();
    document.execCommand('Copy');

    tempItem.parentElement.removeChild(tempItem);
    alert("Коды успешно скопированы")
}

function copyToClipboard(elementName) {
    var e = document.getElementById(elementName).innerText;
    var tempItem = document.createElement('input');

    tempItem.setAttribute('type','text');
    tempItem.setAttribute('display','none');

    let content = e;
    if (e instanceof HTMLElement) {
        content = e.innerHTML;
    }

    tempItem.setAttribute('value',content);
    document.body.appendChild(tempItem);

    tempItem.select();
    document.execCommand('Copy');

    tempItem.parentElement.removeChild(tempItem);
    alert("Код успешно скопирован")
}

function getTextFragment(event) {
    event.preventDefault();

    let selectionSize = document.getElementById('selectionSize').value;
    let textId = document.getElementById('selectionTextId').value;
    let selectionStart = document.getElementById('selectionStart').value;
    let startSize = document.getElementById('startSize').value;
    let type1 = document.getElementById('word-type1').value;
    let type2 = document.getElementById('word-type2').value;
    let type3 = document.getElementById('word-type3').value;
    let searchOnStart = document.getElementById('searchOnStart').checked;

    // покажем спиннер
    document.getElementById("selectionText").innerHTML = "<div class=\"spinner-border  m-5\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";

    $.ajax({
        url: "fragments.php",
        type: "POST",
        data: {selectionSize, textId, selectionStart, startSize, type1, type2, type3, searchOnStart, action: "get-fragment"},
        success: function (result) {
            //console.log(result);
            document.getElementById("selectionText").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("selectionText").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}


function showSingleGraphVisualization(event, mode) {
    event.preventDefault();

    let textId1 = document.getElementById('textId1').value;
    let threshold = document.getElementById('threshold').value;
    let nodal = document.getElementById('nodal').value;
    let vertexesColor = document.getElementById('vertexesColor').value;
    let edgesColor = document.getElementById('edgesColor').value;
    let bgColor = document.getElementById('bgColor').value;
    let vertexesShape = document.getElementById('vertexesShape').value;
    let layout = document.getElementById('layout').value;
    let doubleArrows = document.getElementById('doubleArrows').checked;
    let vertexesSizeCheck = document.getElementById('vertexesSizeCheck').checked;

    // покажем спиннер
    document.getElementById("selectionText").innerHTML = "<div class=\"spinner-border  m-5\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";

    $.ajax({
        url: "graphviz.php",
        type: "POST",
        data: {mode, textId1, threshold, nodal, vertexesColor, edgesColor, bgColor,
            vertexesShape, layout, doubleArrows, vertexesSizeCheck, action: "show-preview"},
        success: function (result) {
            document.getElementById("selectionText").innerHTML = result;
            document.getElementById("exportButton").removeAttribute("disabled");
            document.getElementById("exportExcel").setAttribute("class", "btn btn-primary");

            let exDDMenu = document.getElementById("exDDMenu");
            let items = exDDMenu.getElementsByClassName("dropdown-item");
            for (let i = 0; i < items.length; i++) {
                if(bgColor === "none" && (items[i].id === "exBmp" || items[i].id === "exGif"
                    || items[i].id === "exJpg" || items[i].id === "exJpeg")) {
                    items[i].setAttribute("class", "dropdown-item disabled");
                    continue;
                }
                else items[i].setAttribute("class", "dropdown-item");
                let url = new URL($(items[i]).prop('href'));
                url.searchParams.set("mode", mode);
                url.searchParams.set("textId1", textId1);
                url.searchParams.set("threshold", threshold);
                url.searchParams.set("nodal", nodal);
                url.searchParams.set("vertexesColor", vertexesColor);
                url.searchParams.set("edgesColor", edgesColor);
                url.searchParams.set("bgColor", bgColor);
                url.searchParams.set("vertexesShape", vertexesShape);
                url.searchParams.set("layout", layout);
                url.searchParams.set("doubleArrows", doubleArrows);
                url.searchParams.set("vertexesSizeCheck", vertexesSizeCheck);
                items[i].setAttribute("href", url.href);

            }
            let xlsxBtn = document.getElementById("exportExcel");
            let url = new URL($(xlsxBtn).prop('href'));
            url.searchParams.set("mode", mode);
            url.searchParams.set("textId1", textId1);
            url.searchParams.set("threshold", threshold);
            url.searchParams.set("nodal", nodal);
            url.searchParams.set("vertexesColor", vertexesColor);
            url.searchParams.set("edgesColor", edgesColor);
            url.searchParams.set("bgColor", bgColor);
            url.searchParams.set("vertexesShape", vertexesShape);
            url.searchParams.set("layout", layout);
            url.searchParams.set("doubleArrows", doubleArrows);
            url.searchParams.set("vertexesSizeCheck", vertexesSizeCheck);
            xlsxBtn.setAttribute("href", url.href);
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("selectionText").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function showComparisonGraphVisualization(event, mode) {
    event.preventDefault();

    let textId1 = document.getElementById('textId1').value;
    let textId2 = document.getElementById('textId2').value;
    let threshold = document.getElementById('threshold').value;
    let nodal = document.getElementById('nodal').value;
    let firstColor = document.getElementById('firstColor').value;
    let secondColor = document.getElementById('secondColor').value;
    let commonColor = document.getElementById('commonColor').value;
    let bgColor = document.getElementById('bgColor').value;
    let vertexesShape = document.getElementById('vertexesShape').value;
    let layout = document.getElementById('layout').value;
    let doubleArrows = document.getElementById('doubleArrows').checked;
    let vertexesSizeCheck = document.getElementById('vertexesSizeCheck').checked;
    let showLegend = document.getElementById('showLegend').checked;
    let bAndWMode = document.getElementById('bAndWMode').checked;

    // покажем спиннер
    document.getElementById("selectionText").innerHTML = "<div class=\"spinner-border  m-5\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";

    $.ajax({
        url: "graphviz.php",
        type: "POST",
        data: {mode, textId1, textId2, threshold, nodal, firstColor, secondColor, commonColor, bgColor,
            vertexesShape, layout, doubleArrows, vertexesSizeCheck, showLegend, bAndWMode, action: "show-preview"},
        success: function (result) {
            document.getElementById("selectionText").innerHTML = result;
            document.getElementById("exportButton").removeAttribute("disabled");
            document.getElementById("exportXlsButton").removeAttribute("disabled");

            let exDDMenu = document.getElementById("exDDMenu");
            let items = exDDMenu.getElementsByClassName("dropdown-item");
            for (let i = 0; i < items.length; i++) {
                if(bgColor === "none" && (items[i].id === "exBmp" || items[i].id === "exGif"
                    || items[i].id === "exJpg" || items[i].id === "exJpeg")) {
                    items[i].setAttribute("class", "dropdown-item disabled");
                    continue;
                }
                else items[i].setAttribute("class", "dropdown-item");
                let url = new URL($(items[i]).prop('href'));
                url.searchParams.set("mode", mode);
                url.searchParams.set("textId1", textId1);
                url.searchParams.set("textId2", textId2);
                url.searchParams.set("threshold", threshold);
                url.searchParams.set("nodal", nodal);
                url.searchParams.set("firstColor", firstColor);
                url.searchParams.set("secondColor", secondColor);
                url.searchParams.set("commonColor", commonColor);
                url.searchParams.set("bgColor", bgColor);
                url.searchParams.set("vertexesShape", vertexesShape);
                url.searchParams.set("layout", layout);
                url.searchParams.set("doubleArrows", doubleArrows);
                url.searchParams.set("vertexesSizeCheck", vertexesSizeCheck);
                url.searchParams.set("showLegend", showLegend);
                url.searchParams.set("bAndWMode", bAndWMode);
                items[i].setAttribute("href", url.href);
            }
            let exXlsDDMenu = document.getElementById("exXlsDDMenu");
            items = exXlsDDMenu.getElementsByClassName("dropdown-item");
            for (let i = 0; i < items.length; i++) {
                let url = new URL($(items[i]).prop('href'));
                url.searchParams.set("mode", mode);
                url.searchParams.set("textId1", textId1);
                url.searchParams.set("textId2", textId2);
                url.searchParams.set("threshold", threshold);
                url.searchParams.set("nodal", nodal);
                url.searchParams.set("firstColor", firstColor);
                url.searchParams.set("secondColor", secondColor);
                url.searchParams.set("commonColor", commonColor);
                url.searchParams.set("bgColor", bgColor);
                url.searchParams.set("vertexesShape", vertexesShape);
                url.searchParams.set("layout", layout);
                url.searchParams.set("doubleArrows", doubleArrows);
                url.searchParams.set("vertexesSizeCheck", vertexesSizeCheck);
                url.searchParams.set("showLegend", showLegend);
                url.searchParams.set("bAndWMode", bAndWMode);
                items[i].setAttribute("href", url.href);
            }
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("selectionText").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function removeColormap(event, colormap_id) {
    event.preventDefault();

    $.ajax({
        url: "fragment-colormap.php",
        type: "POST",
        data: {id: colormap_id, action: "remove-colormap"},
        success: function (result) {
            console.log(result);
            window.location.reload();
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("colormap-" + colormap_id).innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function createColormap(event) {
    event.preventDefault();

    let mapID = document.getElementById('mapid').value;
    let textID = document.getElementById('textID').value;
    let comment = document.getElementById('comment').value;
    let colormap = document.getElementById('colormap').value;
    let desclink = document.getElementById('desclink').value;
    let prosLabel = document.getElementById('prosLabel').value;
    let consLabel = document.getElementById('consLabel').value;

    if (mapID) {
        $.ajax({
            url: "fragment-colormap.php",
            type: "POST",
            data: {mapID, textID, comment, colormap, desclink, prosLabel, consLabel, action: "update-colormap"},
            success: function (result) {
                console.log(result);
                window.location.reload();
            },
            error: function (msg) {
                console.log(msg);
                document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                    "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                    "    <span aria-hidden=\"true\">&times;</span>\n" +
                    "  </button>\n" +
                    " </div>");
            }
        });
    } else {
        $.ajax({
            url: "fragment-colormap.php",
            type: "POST",
            data: {textID, comment, colormap, desclink, prosLabel, consLabel, action: "create-colormap"},
            success: function (result) {
                console.log(result);
                window.location.reload();
            },
            error: function (msg) {
                console.log(msg);
                document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                    "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                    "    <span aria-hidden=\"true\">&times;</span>\n" +
                    "  </button>\n" +
                    " </div>");
            }
        });
    }
}

function removeUnusedEntries(e) {
    e.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {action: "remove-unused-entries"},
        success: function (result) {
            console.log(result);
            document.getElementById("card-msg-view").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function removeAllDuplicates(event) {
    event.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {action: "remove-all-duplicates"},
        success: function (result) {
            console.log(result);
            document.getElementById("card-msg-view").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function removeDotEntries(event) {
    event.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {action: "remove-dot-entries"},
        success: function (result) {
            console.log(result);
            document.getElementById("card-msg-view").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function removeAccentEntries(event) {
    event.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {action: "remove-accent-entries"},
        success: function (result) {
            console.log(result);
            document.getElementById("card-msg-view").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function removeSingleDuplicate(event, id) {
    event.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {id, action: "remove-duplicate"},
        success: function (result) {
            console.log(result);
            document.getElementById("card-msg-view").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function showSimilarEntry(event, id) {
    event.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {id, action: "show-similar-entry"},
        success: function (result) {
            console.log(result);
            document.getElementById("msg-similar-" + id).innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("msg-similar-" + id).innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function fixNegativeParams(e) {
    e.preventDefault();

    $.ajax({
        url: "database-stat.php",
        type: "POST",
        data: {action: "fix-negative-params"},
        success: function (result) {
            console.log(result);
            document.getElementById("card-msg-view").innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById("card-msg-view").innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function showEditForm(event, id) {
    event.preventDefault();
    $(id).hide();
}

function sortListByName(event) {
    event.preventDefault();

    var nodeList = document.querySelectorAll('.paper');
    var itemsArray = [];
    var parent = nodeList[0].parentNode;
    for (var i = 0; i < nodeList.length; i++) {
        itemsArray.push(parent.removeChild(nodeList[i]));
    }
    itemsArray.sort(function(nodeA, nodeB) {
        var textA = nodeA.getAttribute('data-title').replace(/[()"']/g, "");
        var textB = nodeB.getAttribute('data-title').replace(/[()"']/g, "");
        return textA.localeCompare(textB);
    })
        .forEach(function(node) {
            parent.appendChild(node)
        });
}

function sortListByYearMagNum(event) {
    event.preventDefault();

    var nodeList = document.querySelectorAll('.paper');
    var itemsArray = [];
    var parent = nodeList[0].parentNode;
    for (var i = 0; i < nodeList.length; i++) {
        itemsArray.push(parent.removeChild(nodeList[i]));
    }
    itemsArray.sort(function(nodeA, nodeB) {
        var yearA = nodeA.getAttribute('data-year');
        var yearB = nodeB.getAttribute('data-year');
        if (yearA !== yearB) {
            return yearA - yearB;
        }
        var magA = nodeA.getAttribute('data-mag');
        var magB = nodeB.getAttribute('data-mag');
        if (magA.localeCompare(magB) !== 0) {
            return magA.localeCompare(magB);
        }
        var numA = nodeA.getAttribute('data-num');
        var numB = nodeB.getAttribute('data-num');
        return numA - numB;
    })
        .forEach(function(node) {
            parent.appendChild(node)
        });
}

function sortListByMagYearNum(event) {
    event.preventDefault();

    var nodeList = document.querySelectorAll('.paper');
    var itemsArray = [];
    var parent = nodeList[0].parentNode;
    for (var i = 0; i < nodeList.length; i++) {
        itemsArray.push(parent.removeChild(nodeList[i]));
    }
    itemsArray.sort(function(nodeA, nodeB) {
        var magA = nodeA.getAttribute('data-mag');
        var magB = nodeB.getAttribute('data-mag');
        if (magA.localeCompare(magB) !== 0) {
            return magA.localeCompare(magB);
        }
        var yearA = nodeA.getAttribute('data-year');
        var yearB = nodeB.getAttribute('data-year');
        if (yearA !== yearB) {
            return yearA - yearB;
        }
        var numA = nodeA.getAttribute('data-num');
        var numB = nodeB.getAttribute('data-num');
        return numA - numB;
    })
        .forEach(function(node) {
            parent.appendChild(node)
        });
}

function sortListBySigns(event) {
    event.preventDefault();

    var nodeList = document.querySelectorAll('.paper');
    var itemsArray = [];
    var parent = nodeList[0].parentNode;
    for (var i = 0; i < nodeList.length; i++) {
        itemsArray.push(parent.removeChild(nodeList[i]));
    }
    itemsArray.sort(function(nodeA, nodeB) {
        var magA = nodeA.getAttribute('data-author1').replace(/[<>]/g, "");
        var magB = nodeB.getAttribute('data-author1').replace(/[<>]/g, "");
        if (magA.localeCompare(magB) !== 0) {
            return magA.localeCompare(magB);
        }

        magA = nodeA.getAttribute('data-author2').replace(/[<>]/g, "");
        magB = nodeB.getAttribute('data-author2').replace(/[<>]/g, "");
        if (magA.localeCompare(magB) !== 0) {
            return magA.localeCompare(magB);
        }

        magA = nodeA.getAttribute('data-author3').replace(/[<>]/g, "");
        magB = nodeB.getAttribute('data-author3').replace(/[<>]/g, "");
        return magA.localeCompare(magB);
    })
        .forEach(function(node) {
            parent.appendChild(node)
        });
}

function updateFilters(displayType) {
    const nodeList = document.querySelectorAll('.paper');
    const yearArray = new Map();
    // журналы
    const magArray = new Map();


    nodeList.forEach(function(item, i) {
        const year = item.getAttribute('data-year');
        if (yearArray.has(year))
            yearArray.set(year, yearArray.get(year) + 1);
        else
            yearArray.set(year, 1);

        const mag = item.getAttribute('data-mag');
        if (magArray.has(mag))
            magArray.set(mag, magArray.get(mag) + 1);
        else
            magArray.set(mag, 1);
    });

    const mapSort1 = new Map([...yearArray.entries()].sort((a, b) => b[1] - a[1]));
    const magSort = new Map([...magArray.entries()].sort((a, b) => b[1] - a[1]));

    const yearBox = document.getElementById('yearList');
    let yearData = "<div class=\"years\">";
    let counter = 0;

    for (let key of mapSort1.keys()) {
        if (counter === 4) {
            yearData += "<div class=\"collapse\" id=\"collapseYearFilters\">";
        }

        yearData += "<div class=\"checkbox\"><label><input type=\"checkbox\" rel=\"" + key + "\" onchange=\"changeFilter('" + displayType + "');\"/> " + key + " (" + mapSort1.get(key) + ")</label></div>";
        counter++;
    }
    if (counter > 4) {
        yearData += "</div></div>";
        yearData += "<a data-toggle=\"collapse\" href=\"#collapseYearFilters\" role=\"button\" aria-expanded=\"false\" aria-controls=\"collapseExample\">Показать/скрыть все</a>";
    }

    yearBox.innerHTML = "<div>" + yearData + "</div>";

    const magBox = document.getElementById('magazineList');
    let magData = "<div class=\"mags\">";
    counter = 0;

    for (let key of magSort.keys()) {
        if (counter === 4) {
            magData += "<div class=\"collapse\" id=\"collapseMagFilters\">";
        }

        magData += "<div class=\"checkbox\"><label><input type=\"checkbox\" rel=\"" + key + "\" onchange=\"changeFilter('" + displayType + "');\"/> " + key + " (" + magSort.get(key) + ")</label></div>";
        counter++;
    }
    if (counter > 4) {
        magData += "</div></div>";
        magData += "<a data-toggle=\"collapse\" href=\"#collapseMagFilters\" role=\"button\" aria-expanded=\"false\" aria-controls=\"collapseExample\">Показать/скрыть все</a>";
    }

    magBox.innerHTML = "<div>" + magData + "</div>";
}

function changeFilter(displayType) {
    const yearCbs = document.querySelectorAll(".years input[type='checkbox']");
    const magCbs = document.querySelectorAll(".mags input[type='checkbox']");
    const textListsCbs  =document.querySelectorAll(".textLists input[type='checkbox']");

    console.log(textListsCbs.length);
    const filters = {
        years: getClassOfCheckedCheckboxes(yearCbs),
        mags: getClassOfCheckedCheckboxes(magCbs),
        textLists: getClassOfCheckedCheckboxes(textListsCbs)
    };

    filterResults(filters, displayType);
}

function getClassOfCheckedCheckboxes(checkboxes) {
    var classes = [];

    if (checkboxes && checkboxes.length > 0) {
        for (var i = 0; i < checkboxes.length; i++) {
            var cb = checkboxes[i];

            if (cb.checked) {
                classes.push(cb.getAttribute("rel"));
            }
        }
    }
    //console.log(classes);

    return classes;
}

Object.defineProperty(Array.prototype, 'unique', {
    enumerable: false,
    configurable: false,
    writable: false,
    value: function() {
        var a = this.concat();
        for(var i=0; i<a.length; ++i) {
            for(var j=i+1; j<a.length; ++j) {
                if(a[i] === a[j])
                    a.splice(j--, 1);
            }
        }

        return a;
    }
});

function filterResults(filters, displayType) {
    const nodeList = document.querySelectorAll('.paper');
    let hiddenElems = [];

    let textListItems = [];
    if (filters.textLists.length > 0) {
        for (let textListsKey in filters.textLists) {
            let curList = filters.textLists[textListsKey].split(",");
            textListItems = textListItems.concat(curList).unique();
            console.log("filter", curList, textListItems);
        }
    }
    console.log(textListItems);

    if (textListItems.length > 0) {
        for (var j = 0; j < nodeList.length; j++) {
            if (textListItems.indexOf(nodeList[j].getAttribute('data-id')) < 0) {
                hiddenElems.push(nodeList[j]);
            }
        }
    }

    // фильтрация по годам
    for (var i = 0; i < nodeList.length; i++) {
        var el = nodeList[i];
        if (filters.years.length > 0 && hiddenElems.indexOf(el) < 0 && filters.years.indexOf(el.getAttribute('data-year')) < 0) {
            hiddenElems.push(el);
        }
    }

    // фильтрация по журналам
    for (i = 0; i < nodeList.length; i++) {
        el = nodeList[i];
        if (filters.mags.length > 0 && hiddenElems.indexOf(el) < 0 && filters.mags.indexOf(el.getAttribute('data-mag')) < 0) {
            hiddenElems.push(el);
        }
    }

    // отображение элементов
    for (i = 0; i < nodeList.length; i++) {
        nodeList[i].style.display = displayType;
    }

    if (hiddenElems.length <= 0) {
        return;
    }

    for (i = 0; i < hiddenElems.length; i++) {
        hiddenElems[i].style.display = "none";
    }
}

function filterTableByTextList(event) {
    event.preventDefault();

    let textId = document.getElementById('selectionTextId').value;
    if (textId.length > 0) {
        let textItems = textId.split(",");

        for (const textIdKey in textItems) {
            let nodeCheck = document.getElementById(textItems[textIdKey]);
            if (nodeCheck != null)
                nodeCheck.checked = true;
        }
    }
}

function compareGiniGraphs(event) {
    event.preventDefault();
    let graph1 = document.getElementById('firstGraph').value;
    let graph2 = document.getElementById('secondGraph').value;
    let insertCost = document.getElementById('insertCost').value;
    let updateCost = document.getElementById('updateCost').value;
    let updateCloseCost = document.getElementById('updateCloseCost').value;
    let updateCloseLevel = document.getElementById('updateCloseLevel').value;
    let deleteCost = document.getElementById('deleteCost').value;
    let deepLevel1 = document.getElementById('deepLevel1').value;
    let deepLevel2 = document.getElementById('deepLevel2').value;

    document.getElementById('compare-result-gini').innerHTML = "<div class=\"spinner-border\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";
    $.ajax({
        url: "graph-compare.php",
        type: "POST",
        data: {view: 'compare', action: "compareGini", graph1, graph2, insertCost, updateCost, updateCloseCost, updateCloseLevel, deleteCost, deepLevel1, deepLevel2},
        success: function (result) {
            console.log(result);
            document.getElementById('compare-result-gini').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('compare-result-gini').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}

function compareNameGraphs(event) {
    event.preventDefault();
    let graph1 = document.getElementById('firstGraphByName').value;
    let graph2 = document.getElementById('secondGraphByName').value;
    let insertCost = document.getElementById('insertCostByName').value;
    let updateCost = document.getElementById('updateCostByName').value;
    let updateCloseCost = document.getElementById('updateCloseCostByName').value;
    let updateCloseLevel = document.getElementById('updateCloseLevelByName').value;
    let updatePart = document.getElementById('updatePartByName').value;
    let updateClosePart = document.getElementById('updateClosePartByName').value;
    let deleteCost = document.getElementById('deleteCostByName').value;
    let deepLevel1 = document.getElementById('deepLevel1BN').value;
    let deepLevel2 = document.getElementById('deepLevel2BN').value;

    document.getElementById('compare-result-name').innerHTML = "<div class=\"spinner-border\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";
    $.ajax({
        url: "graph-compare.php",
        type: "POST",
        data: {view: 'compare', action: "compareNameGini", graph1, graph2, insertCost, updateCost, updateCloseCost, updateCloseLevel, deleteCost, updatePart, updateClosePart, deepLevel1, deepLevel2},
        success: function (result) {
            console.log(result);
            document.getElementById('compare-result-name').innerHTML = result;
        },
        error: function (msg) {
            console.log(msg);
            document.getElementById('compare-result-name').innerHTML = (msg.responseText ? msg.responseText :
                "<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">Error: " + msg.statusText + "<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\">\n" +
                "    <span aria-hidden=\"true\">&times;</span>\n" +
                "  </button>\n" +
                " </div>");
        }
    });
}