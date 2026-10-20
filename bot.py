import os, sqlite3, logging, random, threading
from datetime import date, time as dtime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

MSK = timezone(timedelta(hours=3))
SEND_HOUR, SEND_MINUTE = 17, 0
PER_DIFF = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chef")

DB_FILE = os.getenv("DB_PATH", "chef.db")
DIFF_LABEL = {"easy": "🟢 Простой", "medium": "🟡 Средний", "hard": "🔴 Сложный"}
DIFF_ORDER = ["easy", "medium", "hard"]

R = [
{"id":"aglio","name":"Спагетти альо и олио","cuisine":"Италия","difficulty":"easy","time_min":15,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"спагетти","grams":200,"unit":"г"},{"name":"чеснок","grams":15,"unit":"г"},{"name":"оливковое масло","grams":40,"unit":"мл"},{"name":"перец чили хлопьями","grams":2,"unit":"г"},{"name":"петрушка","grams":10,"unit":"г"},{"name":"соль","grams":5,"unit":"г"}],
 "steps":["Поставьте кастрюлю с водой на сильный огонь, добавьте соль.","Нарежьте чеснок тонкими слайсами, петрушку порубите.","В сковороде разогрейте масло, добавьте чеснок и чили, обжаривайте 2 мин на среднем огне — чеснок не должен потемнеть.","Отварите спагетти аль денте (на 1 мин меньше, чем на пачке).","Переложите спагетти в сковороду, добавьте 2–3 ст. л. воды от варки, перемешайте.","Снимите с огня, посыпьте петрушкой, подавайте немедленно."],
 "origin":"Классика неаполитанской кухни. Название значит «с чесноком и маслом». В оригинале сыр не используется.",
 "substitutions":{"спагетти":["лингвини","пенне","капеллини"],"перец чили хлопьями":["свежий чили","кайенский перец"],"петрушка":["базилик","зелёный лук"]}},
{"id":"quesadilla","name":"Кесадилья с сыром","cuisine":"Мексика","difficulty":"easy","time_min":10,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"тортилья пшеничная","grams":120,"unit":"г"},{"name":"сыр чеддер","grams":120,"unit":"г"},{"name":"фасоль консервированная","grams":100,"unit":"г"},{"name":"сальса","grams":60,"unit":"г"},{"name":"масло растительное","grams":10,"unit":"мл"}],
 "steps":["Разогрейте сухую сковороду на среднем огне.","На половину тортильи выложите сыр и фасоль, сложите пополам.","Обжаривайте 2–3 мин с каждой стороны до золотистой корочки.","Разрежьте на треугольники, подавайте с сальсой."],
 "origin":"Блюдо северной Мексики и Техаса. Название от исп. queso — «сыр».",
 "substitutions":{"сыр чеддер":["моцарелла","гауда","сулугуни"],"тортилья пшеничная":["тортилья кукурузная","лаваш"],"сальса":["гуакамоле","сметана"]}},
{"id":"greek","name":"Греческий салат","cuisine":"Греция","difficulty":"easy","time_min":15,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"помидоры","grams":300,"unit":"г"},{"name":"огурец","grams":200,"unit":"г"},{"name":"перец болгарский","grams":150,"unit":"г"},{"name":"лук красный","grams":60,"unit":"г"},{"name":"сыр фета","grams":150,"unit":"г"},{"name":"оливки каламата","grams":80,"unit":"г"},{"name":"оливковое масло","grams":40,"unit":"мл"},{"name":"орегано сушёный","grams":3,"unit":"г"}],
 "steps":["Нарежьте помидоры крупно, огурец — полукружьями, перец — кольцами, лук — тонкими полукольцами.","Сложите овощи в миску, добавьте оливки.","Сверху положите фету целым куском или крупно поломайте.","Полейте маслом, посыпьте орегано, аккуратно перемешайте."],
 "origin":"В Греции известен как «хориатики» — «деревенский салат». Фету традиционно кладут целым куском.",
 "substitutions":{"сыр фета":["брынза","сулугуни","козий сыр"],"оливки каламата":["оливки без косточки","каперсы"],"орегано сушёный":["тимьян","базилик"]}},
{"id":"shakshuka","name":"Шакшука","cuisine":"Израиль","difficulty":"easy","time_min":20,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"яйцо","grams":200,"unit":"г"},{"name":"помидоры","grams":400,"unit":"г"},{"name":"перец болгарский","grams":150,"unit":"г"},{"name":"лук репчатый","grams":100,"unit":"г"},{"name":"чеснок","grams":10,"unit":"г"},{"name":"паприка","grams":3,"unit":"г"},{"name":"кумин молотый","grams":2,"unit":"г"},{"name":"оливковое масло","grams":30,"unit":"мл"},{"name":"соль","grams":5,"unit":"г"},{"name":"зелень","grams":20,"unit":"г"}],
 "steps":["Обжарьте лук и перец на масле 5 мин.","Добавьте чеснок, паприку и кумин, готовьте 1 мин.","Добавьте помидоры, тушите 10 мин до густоты.","Сделайте ложкой лунки, аккуратно вбейте яйца.","Накройте крышкой, готовьте 5–7 мин до схватывания белка.","Посыпьте зеленью, подавайте со свежим хлебом."],
 "origin":"Блюдо ближневосточной кухни. Название от ивр. «смесь». Популярный завтрак в Израиле.",
 "substitutions":{"помидоры":["томаты в собственном соку","пассата"],"паприка":["чили","харисса"],"зелень":["петрушка","кинза"]}},
{"id":"miso","name":"Мисо-суп","cuisine":"Япония","difficulty":"easy","time_min":15,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"паста мисо","grams":40,"unit":"г"},{"name":"тофу","grams":150,"unit":"г"},{"name":"водоросли вакаме","grams":5,"unit":"г"},{"name":"лук зелёный","grams":20,"unit":"г"},{"name":"вода","grams":800,"unit":"мл"},{"name":"даси","grams":10,"unit":"г"}],
 "steps":["Нагрейте воду, растворите даси, доведите почти до кипения.","Добавьте тофу кубиками и вакаме, прогрейте 1 мин.","Снимите с огня — мисо нельзя кипятить.","Растворите пасту мисо в половнике бульона, верните в кастрюлю.","Разлейте по чашкам, посыпьте зелёным луком."],
 "origin":"Мисо-суп — ежедневный завтрак в Японии. Мисо нельзя кипятить: теряется аромат и погибают полезные культуры.",
 "substitutions":{"даси":["бульон куриный","бульон овощной"],"тофу":["сыр адыгейский","курица"],"водоросли вакаме":["шпинат","нори"]}},
{"id":"padthai","name":"Пад Тай","cuisine":"Таиланд","difficulty":"medium","time_min":25,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"лапша рисовая","grams":150,"unit":"г"},{"name":"креветки","grams":200,"unit":"г"},{"name":"яйцо","grams":100,"unit":"г"},{"name":"соус рыбный","grams":20,"unit":"мл"},{"name":"соус тамариндовый","grams":30,"unit":"мл"},{"name":"сахар пальмовый","grams":15,"unit":"г"},{"name":"арахис","grams":40,"unit":"г"},{"name":"лук зелёный","grams":30,"unit":"г"},{"name":"чеснок","grams":10,"unit":"г"},{"name":"масло растительное","grams":30,"unit":"мл"}],
 "steps":["Замочите лапшу в тёплой воде на 15 мин, откиньте.","Смешайте рыбный соус, тамариндовый соус и сахар.","Раскалите вок на сильном огне, добавьте масло и чеснок, обжарьте 20 сек.","Добавьте креветки, обжаривайте 2 мин до розового цвета.","Сдвиньте креветки в сторону, вбейте яйцо, быстро размешайте.","Добавьте лапшу и соус, перемешивайте 2–3 мин.","Снимите с огня, добавьте зелёный лук и арахис."],
 "origin":"Уличная классика Таиланда. Баланс четырёх вкусов — кислого, сладкого, солёного и острого — основа тайской кухни.",
 "substitutions":{"креветки":["курица","тофу","свинина"],"соус тамариндовый":["сок лайма + коричневый сахар"],"сахар пальмовый":["коричневый сахар","мед"],"арахис":["кешью","семечки"]}},
{"id":"ratatouille","name":"Рататуй","cuisine":"Франция","difficulty":"medium","time_min":50,"servings_base":4,"oven_temp_c":180,
 "ingredients":[{"name":"баклажан","grams":400,"unit":"г"},{"name":"кабачок","grams":400,"unit":"г"},{"name":"перец болгарский","grams":300,"unit":"г"},{"name":"помидоры","grams":500,"unit":"г"},{"name":"лук репчатый","grams":150,"unit":"г"},{"name":"чеснок","grams":20,"unit":"г"},{"name":"оливковое масло","grams":60,"unit":"мл"},{"name":"тимьян","grams":3,"unit":"г"},{"name":"соль","grams":8,"unit":"г"}],
 "steps":["Разогрейте духовку до 180 °C.","Нарежьте все овощи кубиками 1–1,5 см.","В сотейнике обжарьте лук и чеснок 3 мин.","Добавьте перец и помидоры, тушите 10 мин до соуса.","Отдельно обжарьте баклажан и кабачок по 5 мин на сильном огне.","Соедините всё в форме, посолите, добавьте тимьян.","Запекайте 25 мин при 180 °C."],
 "origin":"Прованское овощное рагу. Версия запекания слоями — более поздняя, популяризована фильмом «Рататуй».",
 "substitutions":{"баклажан":["цукини","картофель"],"тимьян":["орегано","прованские травы"],"кабачок":["патиссон","тыква"]}},
{"id":"chili","name":"Чили кон карне","cuisine":"Мексика / Техас","difficulty":"medium","time_min":45,"servings_base":4,"oven_temp_c":None,
 "ingredients":[{"name":"фарш говяжий","grams":500,"unit":"г"},{"name":"фасоль красная консервированная","grams":400,"unit":"г"},{"name":"помидоры в собственном соку","grams":400,"unit":"г"},{"name":"лук репчатый","grams":150,"unit":"г"},{"name":"чеснок","grams":15,"unit":"г"},{"name":"перец чили","grams":10,"unit":"г"},{"name":"паприка копчёная","grams":5,"unit":"г"},{"name":"кумин молотый","grams":4,"unit":"г"},{"name":"масло растительное","grams":30,"unit":"мл"},{"name":"соль","grams":8,"unit":"г"}],
 "steps":["Обжарьте лук и чеснок на масле 3 мин.","Добавьте фарш, разбивайте лопаткой, обжаривайте 8 мин до румяности.","Всыпьте специи и чили, перемешайте, готовьте 1 мин.","Добавьте помидоры и фасоль, доведите до кипения.","Тушите 25–30 мин под крышкой, помешивая.","Посолите, дайте постоять 5 мин перед подачей."],
 "origin":"Спорное блюдо: техасцы считают его своим (без фасоли!), мексиканцы — вариантом своих рагу.",
 "substitutions":{"фарш говяжий":["фарш индейки","фарш куриный","соевый фарш"],"фасоль красная консервированная":["фасоль чёрная","чечевица"],"кумин молотый":["зира","кориандр"]}},
{"id":"stroganoff","name":"Бефстроганов","cuisine":"Россия","difficulty":"medium","time_min":30,"servings_base":2,"oven_temp_c":None,
 "ingredients":[{"name":"говядина","grams":400,"unit":"г"},{"name":"лук репчатый","grams":100,"unit":"г"},{"name":"шампиньоны","grams":200,"unit":"г"},{"name":"сметана","grams":150,"unit":"г"},{"name":"мука пшеничная","grams":15,"unit":"г"},{"name":"масло растительное","grams":30,"unit":"мл"},{"name":"соль","grams":5,"unit":"г"},{"name":"перец чёрный","grams":2,"unit":"г"}],
 "steps":["Нарежьте мясо тонкой соломкой, обсушите.","Обжарьте мясо на сильном огне 2 мин, выложите.","В том же масле обжарьте лук и грибы 7 мин.","Посыпьте мукой, перемешайте, готовьте 1 мин.","Добавьте сметану, доведите до кипения.","Верните мясо, тушите 5 мин, посолите и поперчите."],
 "origin":"Придумано в XIX веке поваром Строгановых. Классика — с картофельным пюре.",
 "substitutions":{"сметана":["сливки 20%","йогурт натуральный"],"шампиньоны":["вешенки","белые грибы"],"говядина":["курица","свинина"]}},
{"id":"curry","name":"Курица карри","cuisine":"Индия","difficulty":"medium","time_min":40,"servings_base":4,"oven_temp_c":None,
 "ingredients":[{"name":"курица","grams":800,"unit":"г"},{"name":"лук репчатый","grams":200,"unit":"г"},{"name":"помидоры","grams":300,"unit":"г"},{"name":"йогурт","grams":150,"unit":"г"},{"name":"чеснок","grams":20,"unit":"г"},{"name":"имбирь","grams":15,"unit":"г"},{"name":"карри","grams":10,"unit":"г"},{"name":"кумин","grams":3,"unit":"г"},{"name":"кориандр","grams":3,"unit":"г"},{"name":"масло растительное","grams":40,"unit":"мл"},{"name":"соль","grams":8,"unit":"г"}],
 "steps":["Обжарьте лук на масле 8 мин до золотистого цвета.","Добавьте чеснок и имбирь, готовьте 1 мин.","Всыпьте специи, перемешайте, готовьте 1 мин.","Добавьте помидоры, тушите 5 мин до соуса.","Добавьте курицу кусочками, обжаривайте 5 мин.","Введите йогурт, тушите 20 мин под крышкой.","Посолите, подавайте с рисом."],
 "origin":"«Карри» — общий термин британцев для индийских соусов. В Индии у каждого блюда своё имя.",
 "substitutions":{"йогурт":["кокосовое молоко","сливки"],"курица":["тофу","фасоль"],"карри":["гарам масала","паприка + куркума"]}},
{"id":"coqauvin","name":"Курица по-бургундски","cuisine":"Франция","difficulty":"hard","time_min":120,"servings_base":4,"oven_temp_c":170,
 "ingredients":[{"name":"курица целая","grams":1600,"unit":"г"},{"name":"вино красное сухое","grams":500,"unit":"мл"},{"name":"бекон","grams":100,"unit":"г"},{"name":"морковь","grams":150,"unit":"г"},{"name":"лук репчатый","grams":150,"unit":"г"},{"name":"шампиньоны","grams":200,"unit":"г"},{"name":"чеснок","grams":20,"unit":"г"},{"name":"мука пшеничная","grams":20,"unit":"г"},{"name":"бульон куриный","grams":300,"unit":"мл"},{"name":"тимьян","grams":4,"unit":"г"},{"name":"лавровый лист","grams":1,"unit":"г"},{"name":"масло сливочное","grams":30,"unit":"г"},{"name":"соль","grams":10,"unit":"г"}],
 "steps":["Разделайте курицу на 8 частей, обсушите, посолите.","Обжарьте бекон до хруста, выложите.","В том же жире обжарьте курицу по 4 мин с каждой стороны, выложите.","Обжарьте морковь и лук 5 мин, верните бекон, посыпьте мукой, 1 мин.","Влейте вино, выпарьте 2 мин.","Добавьте бульон, курицу, чеснок, тимьян, лавр. Накройте.","Тушите в духовке при 170 °C 70–80 мин (бедро ≥ 82 °C).","Отдельно обжарьте шампиньоны на сливочном масле, добавьте за 10 мин до конца.","Уварите соус до густоты, верните курицу, подавайте."],
 "origin":"Классика бургундской кухни. Исторически готовили из старого петуха — долгое тушение делало мясо мягким.",
 "substitutions":{"вино красное сухое":["вино белое сухое + 1 ст. л. бальзамика"],"бекон":["грудинка копчёная","панчетта"],"шампиньоны":["вешенки","белые грибы"],"бульон куриный":["вода + концентрат"]}},
{"id":"paella","name":"Паэлья с морепродуктами","cuisine":"Испания","difficulty":"hard","time_min":60,"servings_base":4,"oven_temp_c":None,
 "ingredients":[{"name":"рис для паэльи","grams":400,"unit":"г"},{"name":"креветки","grams":300,"unit":"г"},{"name":"мидии","grams":400,"unit":"г"},{"name":"кальмар","grams":200,"unit":"г"},{"name":"бульон рыбный","grams":1200,"unit":"мл"},{"name":"помидоры","grams":200,"unit":"г"},{"name":"перец болгарский","grams":100,"unit":"г"},{"name":"лук репчатый","grams":100,"unit":"г"},{"name":"чеснок","grams":15,"unit":"г"},{"name":"шафран","grams":0.3,"unit":"г"},{"name":"паприка копчёная","grams":4,"unit":"г"},{"name":"оливковое масло","grams":60,"unit":"мл"},{"name":"соль","grams":10,"unit":"г"}],
 "steps":["Разогрейте бульон, добавьте шафран.","Обжарьте креветки 1 мин с каждой стороны, выложите.","Обжарьте кальмар 2 мин, выложите.","Обжарьте лук, чеснок, перец 5 мин.","Добавьте помидоры и паприку, готовьте 5 мин (софрито).","Всыпьте рис, обжаривайте 2 мин.","Влейте бульон, посолите, разровняйте. Больше не перемешивайте!","10 мин на сильном огне, 10 мин на среднем.","Выложите морепродукты, готовьте 10 мин.","Снимите, накройте фольгой на 5 мин."],
 "origin":"Родом из Валенсии. В оригинале — с кроликом и курицей. Поджаристый рис на дне (socarrat) — особый шик.",
 "substitutions":{"рис для паэльи":["арборио","круглозёрный"],"мидии":["гребешки","раки"],"шафран":["куркума (цвет, не аромат)"],"бульон рыбный":["бульон куриный + рыбный соус"]}},
{"id":"plov","name":"Плов","cuisine":"Узбекистан","difficulty":"hard","time_min":90,"servings_base":4,"oven_temp_c":None,
 "ingredients":[{"name":"рис девзира","grams":500,"unit":"г"},{"name":"баранина","grams":600,"unit":"г"},{"name":"морковь","grams":500,"unit":"г"},{"name":"лук репчатый","grams":200,"unit":"г"},{"name":"чеснок","grams":40,"unit":"г"},{"name":"зира","grams":5,"unit":"г"},{"name":"масло растительное","grams":100,"unit":"мл"},{"name":"соль","grams":12,"unit":"г"},{"name":"вода","grams":800,"unit":"мл"}],
 "steps":["Раскалите масло в казане.","Обжарьте лук до золотистого, затем мясо до корочки.","Добавьте морковь соломкой, обжаривайте 10 мин.","Добавьте зиру, влейте воду, тушите 30 мин (зирвак).","Всыпьте промытый рис ровным слоем, воткните головки чеснока.","Влейте воду на 2 см выше риса, на сильном огне до впитывания.","Накройте, на слабом огне 20 мин.","Дайте постоять 10 мин, аккуратно перемешайте снизу вверх."],
 "origin":"Узбекский плов — ритуал. Рис не перемешивают при готовке, а переворачивают слоями.",
 "substitutions":{"баранина":["говядина","курица"],"рис девзира":["басмати","рис для плова"],"зира":["кумин"]}},
{"id":"moussaka","name":"Мусака","cuisine":"Греция","difficulty":"hard","time_min":100,"servings_base":6,"oven_temp_c":180,
 "ingredients":[{"name":"баклажан","grams":800,"unit":"г"},{"name":"фарш бараний","grams":600,"unit":"г"},{"name":"помидоры","grams":400,"unit":"г"},{"name":"лук репчатый","grams":200,"unit":"г"},{"name":"чеснок","grams":15,"unit":"г"},{"name":"молоко","grams":500,"unit":"мл"},{"name":"мука пшеничная","grams":60,"unit":"г"},{"name":"масло сливочное","grams":60,"unit":"г"},{"name":"сыр твёрдый","grams":100,"unit":"г"},{"name":"корица","grams":2,"unit":"г"},{"name":"соль","grams":10,"unit":"г"}],
 "steps":["Баклажаны нарежьте, посолите, оставьте на 15 мин, обсушите и обжарьте.","Обжарьте лук и чеснок, добавьте фарш, готовьте 8 мин.","Добавьте помидоры и корицу, тушите 20 мин.","Приготовьте бешамель: растопите масло, добавьте муку, готовьте 1 мин, влейте молоко, варите до густоты.","Выложите слоями: баклажан — фарш — баклажан — бешамель — сыр.","Запекайте при 180 °C 45 мин.","Дайте постоять 20 мин перед нарезкой."],
 "origin":"Греческая мусака. Похожие блюда есть на Балканах и Ближнем Востоке, но слоёная версия с бешамель — греческая.",
 "substitutions":{"фарш бараний":["фарш говяжий","фарш куриный"],"баклажан":["кабачок","картофель"],"молоко":["сливки","растительное молоко"]}},
{"id":"tiramisu","name":"Тирамису","cuisine":"Италия","difficulty":"hard","time_min":35,"servings_base":6,"oven_temp_c":None,
 "ingredients":[{"name":"савоярди","grams":250,"unit":"г"},{"name":"маскарпоне","grams":500,"unit":"г"},{"name":"яйцо","grams":200,"unit":"г"},{"name":"сахар","grams":100,"unit":"г"},{"name":"кофе эспрессо","grams":300,"unit":"мл"},{"name":"какао-порошок","grams":15,"unit":"г"},{"name":"ликёр марсала","grams":30,"unit":"мл"}],
 "steps":["Сварите эспрессо, остудите, добавьте марсалу.","Разделите яйца. Желтки взбейте с 70 г сахара до светлой массы.","Введите маскарпоне лопаткой до однородности.","Белки взбейте с оставшимся сахаром до устойчивых пиков.","Аккуратно вмешайте белки движениями снизу вверх.","Окуните савоярди в кофе на 1 сек с каждой стороны.","Слой печенья, половина крема. Повторите.","Затяните плёнкой, уберите в холодильник минимум на 4 часа.","Перед подачей посыпьте какао через сито."],
 "origin":"Из региона Венето. Название — «подними меня вверх», отсылка к бодрящему кофе. Классика без сливок.",
 "substitutions":{"маскарпоне":["сливочный сыр + сливки 33%"],"савоярди":["бисквитное печенье"],"ликёр марсала":["ром","коньяк","без алкоголя"],"кофе эспрессо":["крепкий растворимый"]}},
]

BY_ID = {r["id"]: r for r in R}

def db():
    c = sqlite3.connect(DB_FILE); c.row_factory = sqlite3.Row; return c

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, chat_id INTEGER,
            servings INTEGER DEFAULT 2, excluded TEXT DEFAULT '', active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER, recipe_id TEXT, PRIMARY KEY(user_id, recipe_id));
        CREATE TABLE IF NOT EXISTS history(user_id INTEGER, recipe_id TEXT, sent_on TEXT,
            PRIMARY KEY(user_id, recipe_id, sent_on));
        """)

def ensure_user(uid):
    with db() as c: c.execute("INSERT OR IGNORE INTO users(user_id, chat_id) VALUES(?,?)", (uid, uid))

def get_user(uid):
    with db() as c: return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def set_servings(uid, n):
    with db() as c: c.execute("UPDATE users SET servings=? WHERE user_id=?", (n, uid))

def set_excluded(uid, words):
    with db() as c: c.execute("UPDATE users SET excluded=? WHERE user_id=?", (",".join(words), uid))

def favorites_list(uid):
    with db() as c:
        return [r["recipe_id"] for r in c.execute(
            "SELECT recipe_id FROM favorites WHERE user_id=? ORDER BY rowid DESC", (uid,))]

def toggle_fav(uid, rid):
    with db() as c:
        ex = c.execute("SELECT 1 FROM favorites WHERE user_id=? AND recipe_id=?", (uid, rid)).fetchone()
        if ex:
            c.execute("DELETE FROM favorites WHERE user_id=? AND recipe_id=?", (uid, rid)); return False
        c.execute("INSERT INTO favorites(user_id, recipe_id) VALUES(?,?)", (uid, rid)); return True

def allowed(r, excluded):
    if not excluded: return True
    hay = " ".join(i["name"].lower() for i in r["ingredients"])
    return not any(w in hay for w in excluded)

def build_daily(uid, excluded, today_iso):
    with db() as c:
        recent = {r["recipe_id"] for r in c.execute(
            "SELECT recipe_id FROM history WHERE user_id=? AND sent_on >= date(?, '-7 day')",
            (uid, today_iso))}
    menu = {}
    for d in DIFF_ORDER:
        pool = [r for r in R if r["difficulty"] == d and allowed(r, excluded)]
        fresh = [r for r in pool if r["id"] not in recent]
        random.shuffle(fresh); random.shuffle(pool)
        chosen = fresh[:PER_DIFF]
        for r in pool:
            if len(chosen) >= PER_DIFF: break
            if r not in chosen: chosen.append(r)
        menu[d] = chosen
        with db() as c:
            for r in chosen:
                c.execute("INSERT OR IGNORE INTO history(user_id, recipe_id, sent_on) VALUES(?,?,?)",
                          (uid, r["id"], today_iso))
    return menu

def menu_text(menu, today):
    lines = [f"👨‍🍳 *Шеф Мира* — меню на {today}", ""]
    for d in DIFF_ORDER:
        lines.append(f"*{DIFF_LABEL[d]}*")
        if not menu[d]: lines.append("_нет подходящих рецептов — проверьте /exclude_")
        for r in menu[d]:
            lines.append(f"• {r['name']} — {r['cuisine']}, ~{r['time_min']} мин")
        lines.append("")
    lines.append("Нажмите на блюдо, чтобы открыть рецепт.")
    return "\n".join(lines)

def menu_kb(menu):
    kb = []
    for d in DIFF_ORDER:
        row = [InlineKeyboardButton(r["name"], callback_data=f"r:{r['id']}") for r in menu[d]]
        if row: kb.append(row)
    return InlineKeyboardMarkup(kb)

def card_text(r, servings):
    k = servings / r["servings_base"]
    out = [f"*{r['name']}*",
           f"🌍 {r['cuisine']} · {DIFF_LABEL[r['difficulty']]} · ⏱ {r['time_min']} мин", "",
           f"*Ингредиенты ({servings} порц.):*"]
    for i in r["ingredients"]:
        out.append(f"• {i['name']} — {round(i['grams'] * k)} {i['unit']}")
    if r.get("oven_temp_c"): out.append(f"🌡 Температура: {r['oven_temp_c']} °C")
    out += ["", "*Приготовление:*"]
    for n, s in enumerate(r["steps"], 1): out.append(f"{n}. {s}")
    if r.get("origin"): out += ["", f"📖 {r['origin']}"]
    return "\n".join(out)

def card_kb(r, uid):
    fav = r["id"] in favorites_list(uid)
    label = "💔 Убрать из избранного" if fav else "⭐ В избранное"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Замена ингредиента", callback_data=f"s:{r['id']}")],
        [InlineKeyboardButton(label, callback_data=f"f:{r['id']}")],
        [InlineKeyboardButton("◀️ К меню", callback_data="menu")],
    ])

async def send_menu(bot, chat_id, uid):
    row = get_user(uid); servings = row["servings"] if row else 2
    excluded = [w for w in ((row["excluded"] if row else "") or "").split(",") if w.strip()]
    today = date.today().isoformat()
    menu = build_daily(uid, excluded, today)
    await bot.send_message(chat_id, menu_text(menu, today),
                           parse_mode="Markdown", reply_markup=menu_kb(menu))

async def send_card(bot, chat_id, uid, rid):
    row = get_user(uid); servings = row["servings"] if row else 2
    r = BY_ID[rid]
    await bot.send_message(chat_id, card_text(r, servings),
                           parse_mode="Markdown", reply_markup=card_kb(r, uid))

async def cmd_start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ensure_user(u.effective_user.id)
    await u.message.reply_text(
        "👨‍🍳 *Шеф Мира*\n\n"
        "Каждый вечер в *17:00 МСК* присылаю 15 рецептов: 5 простых, 5 средних, 5 сложных.\n\n"
        "/menu — меню на сегодня\n/more — ещё рецепты\n/favorites — избранное\n"
        "/servings 4 — количество порций\n"
        "/exclude лук, чеснок — исключить продукты\n"
        "/exclude — очистить исключения",
        parse_mode="Markdown")
    await send_menu(ctx.bot, u.effective_chat.id, u.effective_user.id)

async def cmd_menu(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ensure_user(u.effective_user.id)
    await send_menu(ctx.bot, u.effective_chat.id, u.effective_user.id)

async def cmd_more(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ensure_user(u.effective_user.id)
    await send_menu(ctx.bot, u.effective_chat.id, u.effective_user.id)

async def cmd_fav(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ensure_user(u.effective_user.id)
    favs = [f for f in favorites_list(u.effective_user.id) if f in BY_ID]
    if not favs:
        await u.message.reply_text("Избранное пустое. Нажмите ⭐ под рецептом."); return
    kb = [[InlineKeyboardButton(BY_ID[f]["name"], callback_data=f"r:{f}")] for f in favs]
    await u.message.reply_text("⭐ *Избранное*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cmd_servings(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ensure_user(u.effective_user.id)
    if not ctx.args or not ctx.args[0].isdigit():
        await u.message.reply_text("Использование: /servings 4"); return
    n = max(1, min(12, int(ctx.args[0]))); set_servings(u.effective_user.id, n)
    await u.message.reply_text(f"Готовлю рецепты на {n} порций.")

async def cmd_exclude(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ensure_user(u.effective_user.id)
    if not ctx.args:
        set_excluded(u.effective_user.id, []); await u.message.reply_text("Список исключений очищен."); return
    words = sorted({w.strip().lower() for w in " ".join(ctx.args).split(",") if w.strip()})
    set_excluded(u.effective_user.id, words)
    await u.message.reply_text("Исключены: " + ", ".join(words))

async def on_cb(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    d = q.data; uid = q.from_user.id
    if d == "menu": await send_menu(ctx.bot, q.message.chat_id, uid); return
    if d.startswith("r:"): await send_card(ctx.bot, q.message.chat_id, uid, d[2:]); return
    if d.startswith("s:"):
        r = BY_ID[d[2:]]; subs = r.get("substitutions") or {}
        if not subs: await q.message.reply_text("Для этого блюда замены не заданы."); return
        lines = [f"*Замены для «{r['name']}»*", ""] + [f"• {k} → {', '.join(v)}" for k, v in subs.items()]
        await q.message.reply_text("\n".join(lines), parse_mode="Markdown"); return
    if d.startswith("f:"):
        rid = d[2:]; added = toggle_fav(uid, rid)
        await q.answer("Добавлено ⭐" if added else "Удалено")
        try: await q.edit_message_reply_markup(reply_markup=card_kb(BY_ID[rid], uid))
        except Exception: pass

async def daily_job(ctx: ContextTypes.DEFAULT_TYPE):
    with db() as c:
        users = c.execute("SELECT chat_id, user_id FROM users WHERE active=1").fetchall()
    log.info("Daily send to %d users", len(users))
    for x in users:
        try: await send_menu(ctx.bot, x["chat_id"], x["user_id"])
        except Exception: log.exception("send failed for %s", x["user_id"])

class Health(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def start_health():
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Health).serve_forever()

def main():
    init_db()
    threading.Thread(target=start_health, daemon=True).start()
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("more", cmd_more))
    app.add_handler(CommandHandler("favorites", cmd_fav))
    app.add_handler(CommandHandler("servings", cmd_servings))
    app.add_handler(CommandHandler("exclude", cmd_exclude))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.job_queue.run_daily(daily_job, time=dtime(SEND_HOUR, SEND_MINUTE, tzinfo=MSK))
    log.info("Bot started, daily at %02d:%02d MSK", SEND_HOUR, SEND_MINUTE)
    app.run_polling()

if __name__ == "__main__":
    main()
