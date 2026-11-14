const $=s=>document.querySelector(s),A=$('#app');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ls={get:k=>{try{return localStorage.getItem(k)}catch{return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch{}},del:k=>{try{localStorage.removeItem(k)}catch{}}};
let lang=ls.get('lang')||'ru',pair=ls.get('pair')||'ba-ru',tok=ls.get('tok'),me=null,T={},CFG={goal:5,min_voters:3,noise:20,share:60,tts:false};

// ---------- интерфейс на двух языках: [русский, башкирский] ----------
const D={
home:['Главная','Баш бит'],learn:['Интересное','Ҡыҙыҡлы'],streak:['Серия','Рәттәнлек'],xp:['Опыт','Тәжрибә'],profile:['Профиль','Профиль'],
streakNow:['Серия сейчас','Хәҙерге рәттәнлек'],streakBest:['Лучшая серия','Иң яҡшы рәттәнлек'],daysDone:['Дней с выполненной нормой','Норма үтәлгән көндәр'],
streakRule:['Огонёк держат {goal} перевода в день. Пропустили день — серия начинается заново, но если пропущен ровно один день, её можно восстановить за XP прямо на этой странице. Задания из «Интересного» в норму не входят.','Утты көнөнә {goal} тәржемә тота. Бер көн ҡалдырһағыҙ, рәттәнлек яңынан башлана, әммә бер генә көн ҡалдырылһа, уны ошо биттә XP-ға кире ҡайтарып була. «Ҡыҙыҡлы» биремдәре нормаға инмәй.'],
last28:['Последние 28 дней','Һуңғы 28 көн'],todayLeft:['Сегодня осталось','Бөгөн ҡалды'],keepGoing:['Доделать норму','Норманы тамамларға'],
level:['Уровень','Кимәл'],toNext:['До следующего уровня','Киләһе кимәлгә тиклем'],xpTotal:['Всего опыта','Барлыҡ тәжрибә'],
xpFrom:['Откуда опыт','Тәжрибә ҡайҙан'],xpTr:['За переводы','Тәржемәләр өсөн'],xpLe:['За «Интересное»','«Ҡыҙыҡлы» өсөн'],
howXp:['Как заработать опыт','Тәжрибәне нисек йыйырға'],
xpR1:['Перевод или подтверждение','Тәржемә йәки раҫлау'],xpR2:['Найденная подставная ошибка','Табылған махсус хата'],xpR3:['Поверили подставной ошибке','Махсус хатаға ышандығыҙ'],
xpR4:['Вопрос с подвохом','Хәйләле һорау'],xpR5:['Собранное предложение','Төҙөлгән һөйләм'],xpR6:['Зажжённый огонёк (дневная норма)','Ҡабынған ут (көнлөк норма)'],xpNote:['За «Интересное» — не больше 50 XP в день.','«Ҡыҙыҡлы» өсөн — көнөнә 50 XP-тан артыҡ түгел.'],
xpFl:['За огонёк','Ут өсөн'],flameXp:['за зажжённый огонёк','ҡабынған ут өсөн'],lvlShort:['ур.','ким.'],
fixTitle:['Вернуть огонёк','Утты кире ҡайтарырға'],
fixText:['Вчера дневная норма не выполнена, и огонёк погас. Серию {n} дн. ещё можно спасти, потратив {cost} XP — опыт не копится просто так!','Кисә көнлөк норма үтәлмәне, һәм ут һүнде. {n} көнлөк рәттәнлекте {cost} XP түләп ҡотҡарып була!'],
fixBtn:['Восстановить серию за {cost} XP','{cost} XP-ға рәттәнлекте ҡайтарырға'],
fixNoXp:['Не хватает опыта: нужно {cost} XP. Накопите и возвращайтесь — предложение действует только сегодня.','Тәжрибә етмәй: {cost} XP кәрәк. Йыйып килегеҙ — тәҡдим бөгөн генә ғәмәлдә.'],
fixDone:['Огонёк снова горит — серия спасена!','Ут яңынан яна — рәттәнлек ҡотҡарылды!'],
schoolByCode:['Школу и класс ученику выдаёт код класса от учителя — вводить его можно ниже.','Мәктәпте һәм класты уҡыусыға уҡытыусынан алынған класс коды бирә — уны түбәндә индерегеҙ.'],
teacherSchool:['Школа и класс (заполняет учитель, чтобы получить код класса)','Мәктәп һәм класс (класс кодын алыу өсөн уҡытыусы тултыра)'],
since:['На платформе с','Платформала'],roleIs:['Роль','Роль'],
nAnswers:['Переводов','Тәржемә'],nFound:['Найдено ошибок','Табылған хаталар'],nConfirm:['Подтверждений','Раҫлау'],nFix:['Исправлений','Төҙәтеү'],nErr:['Ошибок','Хата'],
openSettings:['Настройки','Көйләүҙәр'],noSchool:['Школа не выбрана','Мәктәп һайланмаған'],
lFacts:['Факты','Факттар'],lQuiz:['Вопросы с подвохом','Хәйләле һорауҙар'],lBuild:['Собери предложение','Һөйләм төҙө'],lTest:['Контрольная','Контроль эш'],
factDay:['Факт дня','Көн факты'],check:['Проверить','Тикшерергә'],clear:['Сбросить','Таҙартырға'],buildHint:['Составьте башкирское предложение из слов. Осторожно: среди них есть лишние!','Һүҙҙәрҙән башҡортса һөйләм төҙөгөҙ. Иғтибар: араларында артыҡ һүҙҙәр бар!'],
translateIt:['Переведите на башкирский:','Башҡортсаға тәржемә итегеҙ:'],rightAns:['Верно!','Дөрөҫ!'],wrongAns:['Неверно.','Дөрөҫ түгел.'],correctIs:['Правильно:','Дөрөҫө:'],
testIntro:['10 заданий: вопросы с подвохом и сборка предложений. Ответ нельзя изменить — думайте головой!','10 бирем: ауыр һорауҙар һәм һөйләм төҙөү. Яуапты үҙгәртеп булмай — уйлап яуап бирегеҙ!'],start:['Начать','Башларға'],
resultT:['Результат','Һөҙөмтә'],again:['Ещё раз','Тағы бер тапҡыр'],grade5:['Отлично!','Бик яҡшы!'],grade4:['Хорошо!','Яҡшы!'],grade3:['Неплохо, но есть над чем поработать.','Насар түгел, әммә эшләргә кәрәк.'],grade2:['Попробуйте ещё раз — у вас получится!','Тағы бер тапҡыр ҡарағыҙ — килеп сығыр!'],
xpCap:['XP за обучение — не больше 50 в день.','Өйрәнеү өсөн XP — көнөнә 50-нән артыҡ түгел.'],question:['Вопрос','Һорау'],translate:['Переводить','Тәржемә'],base:['База','База'],rating:['Рейтинг','Рейтинг'],class:['Класс','Класс'],expert:['Экспертам','Белгестәргә'],admin:['Управление','Идара'],settings:['Настройки','Көйләүҙәр'],
go:['Начать переводить','Тәржемә итә башларға'],days:['дн. подряд','көн рәттән'],level:['Уровень','Кимәл'],
login:['Войти','Инеү'],reg:['Регистрация','Теркәлеү'],email:['Почта','Электрон почта'],pass:['Пароль (от 8 символов)','Пароль (8 символдан кәм түгел)'],passIn:['Пароль','Пароль'],name:['Имя','Исемегеҙ'],code:['Код из письма','Хаттағы код'],
logout:['Выйти','Сығыу'],logoutAll:['Выйти на всех устройствах','Бөтә ҡоролмаларҙан сығыу'],language:['Язык интерфейса','Интерфейс теле'],send:['Отправить','Ебәрергә'],
city:['Город / район','Ҡала / район'],school:['Школа','Мәктәп'],grade:['Класс','Класс'],letter:['Буква','Хәреф'],
comments:['Комментарии','Фекерҙәр'],write:['Напишите комментарий…','Фекерегеҙҙе яҙығыҙ…'],auto:['Автоперевод — проверьте его','Автотәржемә — тикшерегеҙ'],
right:['Перевод верный','Тәржемә дөрөҫ'],fixit:['Исправить','Төҙәтергә'],next:['Дальше','Артабан'],mine:['Ваш перевод…','Һеҙҙең тәржемә…'],
today:['Сегодня','Бөгөн'],ach:['Достижения','Ҡаҙаныштар'],recent:['Последние переводы','Һуңғы тәржемәләр'],sound:['Звуки','Тауыштар'],save:['Сохранить','Һаҡларға'],pairl:['Языковая пара','Тел парлығы'],
listen:['Послушать','Тыңларға'],words:['слов','һүҙ'],found:['найдено ошибок','табылған хаталар'],accuracy:['точность','теүәллек'],
emptyRecent:['Пока пусто — переведите первый фрагмент!','Әлегә буш — тәүге өҙөктө тәржемә итегеҙ!'],
toFlame:['До огонька сегодня','Бөгөнгө утҡа тиклем'],flameOk:['Огонёк сегодня горит!','Бөгөн утығыҙ яна!'],left:['осталось','ҡалды'],
doneTitle:['Дневная норма выполнена!','Көнлөк норма үтәлде!'],doneText:['Огонёк серии горит. Можно отдохнуть — или перевести ещё немного.','Утығыҙ яна. Ял итергә йәки тағы бер аҙ тәржемә итергә мөмкин.'],
more:['Продолжить переводить','Тәржемәне дауам итергә'],noMore:['Новые фрагменты для этой пары закончились — загляните позже или выберите другую пару в настройках.','Был пар өсөн яңы өҙөктәр бөттө — һуңыраҡ килегеҙ йәки көйләүҙәрҙә башҡа пар һайлағыҙ.'],
bravo:['Молодец!','Афарин!'],extraMode:['сверх нормы','норманан тыш'],overGoal:['сверх нормы','норманан тыш'],
trap:['Ловушка! Это был заведомо неверный вариант. Правильно:','Тоҙаҡ! Был махсус яңылыш вариант ине. Дөрөҫө:'],
fixed:['Вы нашли подставную ошибку!','Һеҙ махсус хатаны таптығыҙ!'],
confirmedMsg:['Перевод подтверждён сообществом и попал в базу','Тәржемә берләшмә тарафынан раҫланды һәм базаға инде'],
expertMsg:['Мнения разошлись — случай передан экспертам','Фекерҙәр айырылды — мәсьәлә белгестәргә ебәрелде'],
goalNow:['Дневная норма выполнена — огонёк горит!','Көнлөк норма үтәлде — ут яна!'],
tConfirmed:['Подтверждённые','Раҫланғандар'],tCollecting:['В процессе','Барышта'],tDisputed:['Спорные','Бәхәсле'],tMine:['Мои переводы','Минең тәржемәләр'],
howTitle:['Как это работает','Был нисек эшләй'],
search:['Поиск','Эҙләү'],leading:['лидирует','алда'],votes:['голосов','тауыш'],yourVar:['ваш вариант','һеҙҙең вариант'],expertMark:['решение эксперта','белгес ҡарары'],
skipped:['пропущено латиницей','латиница үткәрелмәне'],
onlyCyr:['В задания попадают только строки на башкирской кириллице: латиницу программа пропускает, чтобы ученики не запоминали неправильное написание.','Биремдәргә башҡорт кириллицаһындағы юлдар ғына инә: латиницаны программа үткәрмәй.'],
cleanLatin:['Спрятать латиницу из заданий','Биремдәрҙән латиницаны йәшерергә'],hidden:['Спрятано фрагментов','Йәшерелгән өҙөктәр'],
recAsk:['К этой фразе записали озвучку. Она звучит правильно?','Был фразаға тауыш яҙҙылар. Ул дөрөҫ яңғырaймы?'],listen:['Послушать','Тыңларға'],recOk:['Подходит','Ярай'],recBad:['Не подходит','Ярамай'],thanksVote:['Спасибо, голос учтён','Рәхмәт, тауыш иҫәпкә алынды'],
recQueue:['Записи голоса на проверке','Тикшереүҙәге тауыш яҙмалары'],recQueueHint:['Запись звучит в заданиях только после голосования учеников и решения эксперта.','Яҙма уҡыусылар тауыш биргәндән һәм белгес раҫлағандан һуң ғына биремдәрҙә яңғырай.'],onVote:['голосуют','тауыш бирәләр'],waitExpert:['ждёт эксперта','белгесте көтә'],reject:['Отклонить','Кире ҡағырға'],
checkEar:['Проверить на слух','Тыңлап тикшерергә'],checkEarHint:['Нажмите на строку — прозвучит её отрезок. Если текст или время неверны, поправьте строку в поле выше и нажмите кнопку ещё раз.','Юлға баҫығыҙ — уның өҙөгө яңғырар. Хата булһа, өҫтәге яланда төҙәтегеҙ.'],
accepted:['Ответ принят','Яуап ҡабул ителде'],
xpLater:['Очки придут, когда ваш вариант подтвердят другие участники и он попадёт в базу','Башҡа ҡатнашыусылар раҫлағас һәм вариант базаға ингәс, баллдар килер'],
allVars:['Все варианты','Бөтә варианттар'],result:['итог','һөҙөмтә'],stConfirmed:['подтверждён','раҫланды'],stExpert:['у экспертов','белгестәрҙә'],stCollecting:['идёт голосование','тауыш биреү бара'],
emptyBase:['Здесь пока пусто. Переводите фрагменты — варианты появятся во вкладках «В процессе» и «Мои переводы».','Бында әлегә буш. Өҙөктәрҙе тәржемә итегеҙ — варианттар «Барышта» һәм «Минең тәржемәләр» бүлектәрендә күренер.'],
sAll:['Все','Барыһы'],sSchool:['Моя школа','Минең мәктәп'],sClass:['Мой класс','Минең класс'],sSchools:['Школы','Мәктәптәр'],
pDay:['День','Көн'],pWeek:['Неделя','Аҙна'],pMonth:['Месяц','Ай'],pYear:['Год','Йыл'],pAll:['Всё время','Бөтә ваҡыт'],
mPoints:['Баллы','Баллар'],mVocab:['Словарный запас','Һүҙлек запасы'],mFixes:['Исправления','Төҙәтеүҙәр'],mClean:['Меньше ошибок','Аҙыраҡ хата'],
needSchool:['Укажите школу и класс в настройках — тогда появится этот рейтинг.','Көйләүҙәрҙә мәктәп һәм класты күрһәтегеҙ — шунда был рейтинг күренер.'],
noData:['За этот период пока нет данных','Был осорға әлегә мәғлүмәт юҡ'],
report:['Отчёт по классу','Класс буйынса хисап'],student:['Ученик','Уҡыусы'],answers:['Ответов','Яуаптар'],fixesS:['Исправл.','Төҙәт.'],errorsS:['Ошибок','Хаталар'],streak:['Серия','Рәттән'],
needClass:['Укажите школу и класс в настройках, чтобы видеть учеников.','Уҡыусыларҙы күреү өсөн көйләүҙәрҙә мәктәп һәм класты күрһәтегеҙ.'],noStudents:['Пока в классе нет учеников — раздайте им код класса ниже.','Әлегә класта уҡыусылар юҡ — уларға түбәндәге класс кодын таратығыҙ.'],
materials:['Материалы для перевода','Тәржемә өсөн материалдар'],mText:['Текст','Текст'],mAudio:['Аудиозапись','Аудиояҙма'],
step1:['Шаг 1.','1‑се аҙым.'],step1t:['Откуда материал','Материал ҡайҙан'],
step2:['Шаг 2.','2‑се аҙым.'],step2t:['Вставьте текст','Текстты ҡуйығыҙ'],step2a:['Загрузите запись','Яҙманы тейәгеҙ'],
step3:['Шаг 3.','3‑сө аҙым.'],step3t:['Как разбить','Нисек бүлергә'],step3a:['Расшифровка с отметками времени','Ваҡыт билдәләре менән текст'],
step4:['Шаг 4.','4‑се аҙым.'],step4a:['Проверьте строки и нарежьте','Юлдарҙы тикшереп, өҙөктәргә бүлегеҙ'],
phAudio:['первое предложение','беренсе һөйләм'],phAudio2:['второе предложение','икенсе һөйләм'],
minS:['мин','мин'],secS:['с','с'],pick:['Выбрать файл','Файл һайларға'],notYet:['выбран, нажмите «Загрузить»','һайланды, «Тейәргә» баҫығыҙ'],onServer:['загружен','тейәлде'],loadingModel:['Скачиваю модель…','Модель алам…'],
tooLongJob:['Слишком долго — попробуйте запись покороче','Бик оҙаҡ — ҡыҫҡараҡ яҙма алығыҙ'],
autoMark:['Автоматическая разметка','Автоматик билдәләү'],
autoHint:['«По паузам» — если текст уже вставлен в поле выше: программа найдёт в записи паузы и расставит время сама, это быстро и точно. «Расшифровать» — если текста нет: модель прослушает запись и напишет его сама, это занимает несколько минут, а текст потом нужно вычитать.','«Тынлыҡтар буйынса» — текст өҫтәге яланда булһа: программа яҙмалағы тынлыҡтарҙы табып, ваҡытты үҙе ҡуя, был тиҙ һәм теүәл. «Расшифровкалау» — текст булмаһа: модель яҙманы тыңлап, текстты үҙе яҙа, был бер нисә минут ала, аҙаҡ уны тикшерергә кәрәк.'],
pausesOnly:['Текст уже есть? Вставьте его в поле выше и нажмите кнопку — программа найдёт паузы и расставит время сама. Чтобы расшифровывать речь без текста, поставьте башкирскую модель (install_asr_ba.bat).','Текст бармы? Уны өҫтәге яланға ҡуйып, төймәгә баҫығыҙ. Текстһыҙ таныу өсөн башҡорт моделен ҡуйығыҙ (install_asr_ba.bat).'],
autoOff:['Автоматическая разметка не установлена: install_asr.bat — быстро и для разметки по паузам, install_asr_ba.bat — башкирская расшифровка речи. Без них отметки времени ставятся вручную.','Һөйләмде таныу ҡуйылмаған — install_asr.bat‑ты эшләтегеҙ йәки ваҡыт билдәләрен ҡулдан яҙығыҙ.'],
doAsr:['Расшифровать запись','Яҙманы расшифровкалау'],doPauses:['Разложить мой текст по паузам','Текстты тынлыҡтар буйынса таратыу'],
working:['Обрабатываю…','Эшкәртәм…'],marked:['Строк размечено','Юл билдәләнде'],needDoc:['Сначала укажите название источника','Башта сығанаҡ исемен яҙығыҙ'],needText:['Вставьте текст в поле нарезки','Нарезка яланына текст ҡуйығыҙ'],
byAudio:['По отметкам времени (аудио)','Ваҡыт билдәләре буйынса (аудио)'],audioSrc:['Аудиоисточник','Аудио сығанаҡ'],
audioHint:['Загрузите аудиофайл, затем нарежьте расшифровку строками вида «00:07 текст» — фрагменты будут ссылаться на отрезки этой записи.','Аудиофайлды тейәгеҙ, аҙаҡ «00:07 текст» рәүешендәге юлдар менән бүлегеҙ — өҙөктәр шул яҙманың киҫәктәренә һылтана.'],
upload:['Загрузить','Тейәргә'],uploaded:['Файл загружен','Файл тейәлде'],needFile:['Выберите файл и укажите название источника','Файл һайлағыҙ һәм сығанаҡ исемен яҙығыҙ'],tooBig:['Файл больше 60 МБ','Файл 60 МБ‑тан ҙурыраҡ'],
listenSrc:['Послушать в записи','Яҙмала тыңларға'],noAudio:['Запись недоступна','Яҙма юҡ'],
slice:['Нарезка материала','Материалды өҙөктәргә бүлеү'],sliceHint:['Вставьте текст на башкирском — он будет разбит на фрагменты с координатами источника.','Башҡортса текст ҡуйығыҙ — ул сығанаҡ координаталары менән өҙөктәргә бүленер.'],
srcDoc:['Источник (произведение / файл)','Сығанаҡ (әҫәр / файл)'],chapter:['Глава','Бүлек'],textPh:['Текст…','Текст…'],bySent:['По предложениям','Һөйләмдәр буйынса'],byPara:['По абзацам','Абзацтар буйынса'],cut:['Нарезать','Бүлергә'],created:['Создано фрагментов','Булдырылған өҙөктәр'],
accept:['Принять','Ҡабул итергә'],noDisputes:['Спорных случаев нет','Бәхәсле осраҡтар юҡ'],decided:['Решение сохранено','Ҡарар һаҡланды'],
users:['Пользователи','Ҡулланыусылар'],nameCol:['Имя','Исем'],roleCol:['Роль','Роль'],blockCol:['Блок','Блок'],addSchool:['Добавить школу','Мәктәп өҫтәргә'],add:['Добавить','Өҫтәргә'],
cityOr:['Город или район','Ҡала йәки район'],schoolName:['Название школы','Мәктәп исеме'],roleChanged:['Роль изменена','Роль үҙгәртелде'],blocked:['Заблокирован','Блокланды'],unblocked:['Разблокирован','Блоктан сығарылды'],schoolAdded:['Школа добавлена','Мәктәп өҫтәлде'],
notSelected:['не выбрана','һайланмаған'],soundOn:['Звук включён','Тауыш ҡабыҙылды'],soundOff:['Звук выключен','Тауыш һүндерелде'],toggle:['Вкл / выкл','Ҡабыҙырға / һүндерергә'],saved:['Сохранено','Һаҡланды'],
codeSent:['Мы отправили код на','Кодты ошо адресҡа ебәрҙек:'],resend:['Отправить код ещё раз','Кодты ҡабат ебәрергә'],newMail:['Новое письмо отправлено','Яңы хат ебәрелде'],devCode:['Почта не настроена, код:','Почта көйләнмәгән, код:'],
tagline:['Переводим вместе — сохраняем башкирский язык','Бергә тәржемә итәбеҙ — башҡорт телен һаҡлайбыҙ'],
b_first:['Первый перевод','Тәүге тәржемә'],b_ten:['10 ответов','10 яуап'],b_fifty:['50 ответов','50 яуап'],b_fix:['3 ошибки найдено','3 хата табылды'],b_streak:['7 дней подряд','7 көн рәттән'],b_vocab:['50 слов','50 һүҙ'],
noNet:['Нет связи с сервером. Проверьте интернет и попробуйте снова','Сервер менән бәйләнеш юҡ. Интернетты тикшереп, ҡабатлап ҡарағыҙ'],oops:['Что-то пошло не так','Нимәлер килеп сыҡманы'],
noVoice:['В этом браузере нет голоса для озвучки','Был браузерҙа уҡыу өсөн тауыш юҡ'],recVoice:['Записать голос','Тауыш яҙырға'],recStop:['Остановить запись','Яҙҙырыуҙы туҡтатырға'],recSaved:['Запись отправлена на проверку: сначала её оценят ученики, потом эксперт','Яҙма тикшереүгә ебәрелде: башта уҡыусылар, аҙаҡ белгес баһалай'],noMic:['Нет доступа к микрофону','Микрофонға рөхсәт юҡ'],
report:['Задание странное','Бирем сәйер'],reportHint:['Фраза и перевод не связаны? Пожалуйтесь — задание уйдёт на проверку.','Һөйләм менән тәржемә бәйле түгелме? Шикәйәт итегеҙ — бирем тикшереүгә китә.'],
reported:['Спасибо! Задание отправлено на проверку.','Рәхмәт! Бирем тикшереүгә ебәрелде.'],reportedHidden:['Спасибо! Задание убрано из выдачи.','Рәхмәт! Бирем сығарылыуҙан алынды.'],
tg:['Telegram-бот','Telegram-бот'],tgLinked:['Telegram привязан — прогресс в боте и на сайте общий.','Telegram бәйләнгән — боттағы һәм сайттағы уңыштар уртаҡ.'],tgHint:['Задания можно выполнять и в Telegram. Бот напомнит о дневной норме.','Бурыстарҙы Telegram-да ла үтәргә мөмкин. Бот көнлөк норма тураһында иҫкәртер.'],
tgLink:['Привязать Telegram','Telegram-ды бәйләргә'],tgOpen:['Открыть бота','Ботты асырға'],
classCode:['Код класса от учителя (если есть)','Уҡытыусынан класс коды (булһа)'],classCodeH:['Код класса','Класс коды'],join:['Присоединиться','Ҡушылырға'],joined:['Вы добавлены в класс','Һеҙ класҡа өҫтәлдегеҙ'],
invite:['Код для учеников','Уҡыусылар өсөн код'],inviteHint:['Ученики вводят этот код при регистрации на сайте или в боте — и сразу попадают в ваш класс.','Уҡыусылар был кодты сайтта йәки ботта теркәлгәндә индерә — һәм шунда уҡ һеҙҙең класҡа эләгә.'],
makeInvite:['Получить код класса','Класс кодын алырға'],csv:['Скачать отчёт (Excel / CSV)','Хисапты йөкләргә (Excel / CSV)'],tgLogin:['Входим через Telegram…','Telegram аша инәбеҙ…'],
credit:['Часть фраз — из датасета «Башкирские трёхъязычные параллельные разговорники» (БГПУ им. М. Акмуллы; издатель — Фонд сохранения и развития башкирского языка), лицензия CC BY 4.0.',
 'Һөйләмдәрҙең бер өлөшө — «Башҡортса өс телле параллель һөйләшмәләр» датасетынан (М. Аҡмулла исемендәге БДПУ; нәшер итеүсе — Башҡорт телен һаҡлау һәм үҫтереү фонды), CC BY 4.0 лицензияһы.']
};
const t=k=>(D[k]?D[k][lang==='ba'?1:0]:k);
const PAIRS={'ba-ru':['башкирский → русский','башҡортса → русса'],'ba-en':['башкирский → английский','башҡортса → инглизсә'],'ba-kk':['башкирский → казахский','башҡортса → ҡаҙаҡса'],'ba-alt':['башкирский → алтайский','башҡортса → алтайса'],'ba-ar':['башкирский → арабский','башҡортса → ғәрәпсә'],'ba-sah':['башкирский → якутский','башҡортса → саха телендә'],'ba-zh':['башкирский → китайский','башҡортса → ҡытайса']};
const pl=p=>(PAIRS[p]||[p,p])[lang==='ba'?1:0];
const ROLES={student:['ученик','уҡыусы'],teacher:['учитель','уҡытыусы'],moderator:['модератор','модератор'],expert:['эксперт','белгес'],admin:['администратор','администратор']};
const rl=r=>(ROLES[r]||[r,r])[lang==='ba'?1:0];

// ---------- приветствия: каждый раз новое ----------
const HELLO=[['Привет','Сәләм'],['Здравствуй','Һаумы'],['Рады видеть','Күреүебеҙгә шатбыҙ'],['С возвращением','Яңынан хуш киләһең']];
const TIMEHELLO=h=>h<5?['Доброй ночи','Хәйерле төн']:h<12?['Доброе утро','Хәйерле иртә']:h<18?['Добрый день','Хәйерле көн']:['Добрый вечер','Хәйерле кис'];
const SUBS=[
 ['Сегодня отличный день для башкирского языка!','Бөгөн — башҡорт теле өсөн иң яҡшы көн!'],
 ['Каждый ваш перевод делает базу языка богаче.','Һәр тәржемәгеҙ тел базаһын байыта.'],
 ['Пять переводов — и огонёк серии не погаснет!','Биш тәржемә — һәм утығыҙ һүнмәй!'],
 ['Найдите подставную ошибку в автопереводе — получите бонус.','Автотәржемәлә махсус хатаны табығыҙ — бүләк алығыҙ.'],
 ['Куница уже приготовила для вас новые фразы.','Һуҫар һеҙгә яңы һөйләмдәр әҙерләне.'],
 ['Маленький шаг каждый день — большой путь за год.','Көн һайын бәләкәй аҙым — йыл буйына ҙур юл.'],
 ['Ваш вариант может стать эталонным переводом.','Һеҙҙең вариант өлгө тәржемә булып ҡалыуы мөмкин.'],
 ['Слушайте фразы — так слова запоминаются быстрее.','Һөйләмдәрҙе тыңлағыҙ — шулай һүҙҙәр тиҙерәк иҫтә ҡала.'],
 ['Вместе мы собираем словарь, которым будут пользоваться школы.','Бергәләп беҙ мәктәптәр файҙаланасаҡ һүҙлек йыябыҙ.']];
const pick=a=>a[Math.floor(Math.random()*a.length)];
function greet(){const g=Math.random()<.5?TIMEHELLO(new Date().getHours()):pick(HELLO);let s=pick(SUBS);if(s===greet.last)s=pick(SUBS);greet.last=s;return [g[lang==='ba'?1:0],s[lang==='ba'?1:0]]}

// ---------- запросы к API ----------
async function api(p,o={}){let r;try{r=await fetch('/api'+p,{method:o.method||'GET',headers:{'Content-Type':'application/json',...(tok?{Authorization:'Bearer '+tok}:{})},body:o.body?JSON.stringify(o.body):void 0})}catch{throw new Error(t('noNet'))}
 let d={};try{d=await r.json()}catch{}
 if(!r.ok){if(r.status===401&&tok){tok=null;ls.del('tok');me=null;location.hash='#/auth'}const m=Array.isArray(d.detail)?d.detail[0].msg:d.detail;throw new Error(m||t('oops'))}return d}

// ---------- звуки интерфейса ----------
let ac;function tone(f,d,ty='sine',v=.16,s=0){if(ls.get('snd')==='0')return;try{ac=ac||new(window.AudioContext||window.webkitAudioContext)();const o=ac.createOscillator(),g=ac.createGain(),n=ac.currentTime+s;o.type=ty;o.frequency.value=f;g.gain.setValueAtTime(v,n);g.gain.exponentialRampToValueAtTime(.001,n+d);o.connect(g).connect(ac.destination);o.start(n);o.stop(n+d)}catch{}}
const SND={click:()=>tone(560,.07,'triangle',.08),ok:()=>{tone(523,.12,'sine',.18);tone(784,.22,'sine',.18,.1)},bad:()=>{tone(220,.18,'sawtooth',.08);tone(165,.3,'sawtooth',.08,.14)},
 win:()=>[392,440,523,587,659,784].forEach((f,i)=>tone(f,.3,'triangle',.16,i*.1)),pop:()=>tone(880,.09,'sine',.1)};
document.addEventListener('click',e=>{if(e.target.closest('button,.nv,.tabs a'))SND.click()},true);

// ---------- озвучка (TTS) ----------
const VOICE={'ba':['ba'],'ru':['ru'],'en':['en'],'kk':['kk','ru'],'ar':['ar'],'zh':['zh'],'sah':['ru'],'alt':['ru']};
let audio=null;
function stopVoice(){try{speechSynthesis.cancel()}catch{}if(audio){audio.pause();audio=null}document.querySelectorAll('.ib.play').forEach(b=>b.classList.remove('play'))}
// Запасной вариант без серверной озвучки: в браузерах нет башкирского голоса, а русский читает ә, ҡ, ң… по буквам.
// Поэтому особые буквы заменяются на близкие по звучанию русские — получается целое слово с акцентом, а не побуквенное чтение.
const BA_V='аеёиоуыэюяәөүАЕЁИОУЫЭЮЯӘӨҮ';
function ba2ru(s){let o='';for(let i=0;i<s.length;i++){const c=s[i],p=s[i-1]||' ',afterCons=/[а-яёәөүғҡңҙҫһ]/i.test(p)&&!BA_V.includes(p)&&!/[йьъ]/i.test(p),up=c!==c.toLowerCase(),l=c.toLowerCase();
 let r={'ғ':'г','ҡ':'к','ң':'н','ҙ':'з','ҫ':'с','һ':'х'}[l];
 if(l==='ә')r=afterCons?'я':'э';else if(l==='ө')r=afterCons?'ё':'о';else if(l==='ү')r=afterCons?'ю':'у';
 o+=r?(up?r.toUpperCase():r):c}return o}
function browserSay(text,lng,btn){if(!('speechSynthesis' in window))return toast(t('noVoice'));const vs=speechSynthesis.getVoices();let v=null;for(const p of VOICE[lng]||['ru']){v=vs.find(x=>x.lang.toLowerCase().startsWith(p));if(v)break}
 if(lng==='ba'&&!v){text=ba2ru(text);v=vs.find(x=>x.lang.toLowerCase().startsWith('ru'));lng='ru'}
 const u=new SpeechSynthesisUtterance(text);if(v){u.voice=v;u.lang=v.lang}else u.lang=lng==='ru'?'ru-RU':lng;u.rate=.9;u.onend=u.onerror=()=>btn&&btn.classList.remove('play');speechSynthesis.speak(u)}
window.say=async(btn,kind,id)=>{const playing=btn.classList.contains('play');stopVoice();if(playing)return;btn.classList.add('play');
 const text=btn.dataset.text,lng=kind==='ba'?'ba':(btn.dataset.lang||'ru');
 if(kind==='ba'&&id){try{const r=await fetch('/api/audio/'+id);if(r.ok){audio=new Audio(URL.createObjectURL(await r.blob()));audio.onended=()=>btn.classList.remove('play');await audio.play();return}}catch{}}
 if(kind==='ba'&&CFG.tts&&id){try{const r=await fetch('/api/tts/'+id);if(r.ok){audio=new Audio(URL.createObjectURL(await r.blob()));audio.onended=()=>btn.classList.remove('play');await audio.play();return}}catch{}}
 browserSay(text,lng,btn)};
const spk=(text,kind,id,lng='')=>`<button type=button class=ib title="${t('listen')}" data-text="${esc(text)}" data-lang="${lng}" onclick="say(this,'${kind}',${id||0})">${ic('speaker')}</button>`;

function confetti(){const c=['#fbe29d','#2f7a74','#775537','#c0ddda','#e9b949','#fff'];for(let i=0;i<46;i++){const e=document.createElement('i');e.className='conf';e.style.cssText=`left:${Math.random()*100}vw;background:${c[i%6]};--dx:${(Math.random()-.5)*300}px;animation-delay:${Math.random()*.4}s`;document.body.append(e);setTimeout(()=>e.remove(),2400)}}
function toast(m){const e=document.createElement('div');e.className='toast';e.textContent=m;document.body.append(e);setTimeout(()=>e.remove(),2600)}
const img=(n,c='')=>`<img src="/static/img/${n}.svg" class="${c}" alt="">`;
const logo=()=>`<img src="/static/img/logo-head.svg" class=lg alt="">`;
// маскот — обводка рисунка: один SVG на настроение, анимация внутри файла
const mascot=(m='happy')=>`<img src="/static/img/marten-${m}.svg" class="mascot" alt="">`;
$('#leaves').innerHTML=[6,19,33,51,68,84].map((x,i)=>`<img class=leaf src="/static/img/${i%2?'leaf2':'leaf'}.svg" style="left:${x}vw;animation-duration:${24+i*4}s;animation-delay:${-i*5}s" alt="">`).join('');

// ---------- иконки (линейные SVG, цвет берут из текста) ----------
const IC={
speaker:'<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
scroll:'<path d="M7 3h11a2 2 0 0 1 2 2v1h-4"/><path d="M16 6v13a2 2 0 0 1-4 0v-1H4v1a2 2 0 0 0 2 2h8"/><path d="M7 3a2 2 0 0 0-2 2v13"/><path d="M9 8h4M9 12h4"/>',
headphones:'<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="14" width="4" height="6" rx="1.5"/><rect x="17" y="14" width="4" height="6" rx="1.5"/>',
arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
star:'<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
book:'<path d="M3 5.5C5.5 4 9 4 12 6c3-2 6.5-2 9-.5V19c-2.5-1.5-6-1.5-9 .5-3-2-6.5-2-9-.5z"/><path d="M12 6v13.5"/>',
search:'<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
award:'<circle cx="12" cy="9" r="6"/><path d="m8.5 14 -1.5 7 5-2.5 5 2.5-1.5-7"/><path d="m12 6 .9 1.9 2 .3-1.5 1.4.4 2-1.8-1-1.8 1 .4-2-1.5-1.4 2-.3z"/>',
check:'<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.7 2.7L16.5 9.5"/>',
tick:'<path d="m5 12.5 4.5 4.5L19 7.5"/>',
alert:'<path d="M12 3.5 2.5 20h19z"/><path d="M12 10v4.5M12 17.5v.01"/>',
party:'<path d="m4 20 5-13 8 8z"/><path d="M14 4v2M19 9h2M17.5 5.5 16 7M11 3.5 11.5 5M20 13.5l-1.5-.5"/>',
bot:'<rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 4v4M9 13v1M15 13v1M9.5 16.5h5"/><circle cx="12" cy="3.5" r="1"/>',
edit:'<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 2.9-6 6.5-6s6.5 2.5 6.5 6"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.2c2.1.8 3.5 2.9 3.5 5.8"/>',
comment:'<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
key:'<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l2 2M15 8l2 2"/>',
scissors:'<circle cx="6" cy="6" r="2.8"/><circle cx="6" cy="18" r="2.8"/><path d="M8.2 7.8 20 18M8.2 16.2 20 6"/>',
school:'<path d="M3 21h18M5 21V10l7-5 7 5v11"/><path d="M10 21v-5h4v5M12 5V2.5h3"/>',
send:'<path d="M21 3 3 10.5l7 2.5 2.5 7z"/><path d="m10 13 4.5-4.5"/>',
trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/><path d="M10 11v6M14 11v6"/>',
download:'<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
abc:'<path d="M3 17 6.5 7 10 17M4.2 14h4.6"/><path d="M13 7v10h3a2.5 2.5 0 0 0 0-5h-3 2.5a2.5 2.5 0 0 0 0-5z"/>',
sound:'<path d="M3 12h2l2-5 3 10 3-14 3 12 2-3h3"/>',
drop:'<path d="M12 3c3.5 4.5 6 7.7 6 11a6 6 0 0 1-12 0c0-3.3 2.5-6.5 6-11z"/>',
puzzle:'<path d="M5 8h3a2 2 0 1 1 4 0h3v3a2 2 0 1 1 0 4v4h-4a2 2 0 1 0-4 0H5v-4a2 2 0 1 0 0-4z"/>',
music:'<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
tamga:'<path d="M12 3l9 9-9 9-9-9z"/><path d="M12 8l4 4-4 4-4-4z"/>',
mountain:'<path d="m2 20 7-12 4 6 3-4 6 10z"/><path d="m7.5 10.5 1.5 1.5 1.5-1.5"/>',
jar:'<path d="M8 3h8M7 6h10l1 3v9a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V9z"/><path d="M6 11h12"/>',
vest:'<path d="M8 3 4 6v13a2 2 0 0 0 2 2h4V9L8 3zM16 3l4 3v13a2 2 0 0 1-2 2h-4V9z"/><path d="M8 3c1 2 2.5 3 4 3s3-1 4-3"/>',
tent:'<path d="M2 20 12 5l10 15z"/><path d="M12 5v15M9 20l3-5 3 5"/>',
hash:'<path d="M9 3 7 21M17 3l-2 18M4 9h17M3 15h17"/>',
home:'<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h5v-6h4v6h5V9.5"/>',
translate:'<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/><path d="M14 20h6"/>',
base:'<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v6.5c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8V5.5"/><path d="M4.5 12v6.2c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8V12"/>',
learn:'<path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.4 1.1 2.2h5c0-.8.4-1.6 1.1-2.2A6 6 0 0 0 12 3z"/>',
rating:'<path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3"/>',
class:'<path d="m2 9 10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5"/><path d="M22 9v6"/>',
expert:'<path d="M12 3v18"/><path d="M7 21h10"/><path d="M4 7h16"/><path d="m6 7-3 7a3 3 0 0 0 6 0zM18 7l-3 7a3 3 0 0 0 6 0z"/>',
admin:'<path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
flame:'<path d="M12 22c4 0 7-2.7 7-6.8 0-3.6-2.4-5.6-4-8.2-.7 1.7-1.5 2.6-2.6 3C12.6 7 11.5 4.6 9.5 2 9.2 6.2 5 8.6 5 14.6 5 19 8 22 12 22z"/><path d="M12 22c-1.7 0-3-1.2-3-3 0-2 1.6-3 2.4-4.6.9 1.4 3.6 2.6 3.6 4.6 0 1.8-1.3 3-3 3z"/>',
gem:'<path d="M6 3h12l4 6-10 12L2 9z"/><path d="M2 9h20M12 21 8 9l4-6 4 6z"/>',
user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>'};
IC.mic='<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>';
const ic=(k,c='ic')=>`<svg class="${c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[k]||''}</svg>`;

// ---------- каркас ----------
const NAV=['home','translate','base','learn','rating','class','expert','admin','settings'];
const can=k=>k==='class'?['teacher','admin'].includes(me.role):k==='expert'?['moderator','expert','admin'].includes(me.role):k==='admin'?me.role==='admin':true;
function shell(){if($('#pg'))return;A.innerHTML=`<div class=shell><nav class=side><div class=logo>${logo()}Тамға</div><div id=nav></div></nav><div class=main><div class=top id=top></div><div id=pg></div></div></div>`}
const MOB_HIDE=['translate','settings'];   // на телефоне до них проще дойти с главной и из шапки
function chrome(page){$('#nav').innerHTML=NAV.filter(k=>can(k)).map(k=>`<a class="nv ${MOB_HIDE.includes(k)?'nv-d':''} ${k===page?'on':''}" href="#/${k}">${ic(k)}<span>${t(k)}</span></a>`).join('');top_(page)}
function top_(page){const h=page||location.hash.slice(2).split('/')[0];
 $('#top').innerHTML=`<a class="ib ${h==='settings'?'on':''}" href="#/settings" title="${t('settings')}">${ic('settings')}</a>
 <span class=chips><a class="chip ${me.streak_today?'':'dim'} ${h==='streak'?'on':''}" href="#/streak" title="${me.streak_today?t('flameOk'):t('toFlame')}"><span class=flame>${ic('flame','ic fl')}</span>${me.streak}<span class=cw> ${t('days')}</span></a><a class="chip ${h==='xp'?'on':''}" href="#/xp">${ic('gem','ic gm')}${me.xp} XP</a><a class="chip ${h==='profile'?'on':''}" href="#/profile">${ic('user')}${esc(me.name)}</a></span>`}
function setPage(html){stopVoice();const p=$('#pg'),go=()=>{p.innerHTML=`<div class=page>${html}</div>`;scrollTo({top:0});fx()};if(p.firstChild&&p.firstChild.classList){p.firstChild.classList.add('out');setTimeout(go,170)}else go()}
function fx(){requestAnimationFrame(()=>{document.querySelectorAll('i[data-w]').forEach(e=>e.style.width=e.dataset.w+'%');document.querySelectorAll('.fg[data-p]').forEach(e=>e.style.strokeDashoffset=e.dataset.p);
 document.querySelectorAll('.cu').forEach(e=>{const v=+e.dataset.v,t0=performance.now();(function f(n){const k=Math.min(1,(n-t0)/900);e.textContent=Math.round(v*(1-Math.pow(1-k,3)));if(k<1)requestAnimationFrame(f)})(t0)})})}
const ring=p=>`<svg class=ring viewBox="0 0 100 100"><defs><linearGradient id=rg x1=0 y1=0 x2=1 y2=1><stop offset=0 stop-color="#e9b949"/><stop offset=1 stop-color="#2f7a74"/></linearGradient></defs><circle class=bg cx=50 cy=50 r=42 /><circle class=fg cx=50 cy=50 r=42 stroke-dasharray="264" stroke-dashoffset="264" data-p="${264-264*Math.min(1,p)}"/></svg>`;
let MP=null;                                   // проигрыватель отрезка аудиоисточника
window.seg=async(b,fid,from,to)=>{try{
 if(MP){MP.pause();MP.remove();const was=MP.dataset.fid;MP=null;document.querySelectorAll('.ib.on').forEach(x=>x.classList.remove('on'));if(was==fid)return}
 const a=new Audio('/api/media/'+fid);a.dataset.fid=fid;MP=a;b.classList.add('on');
 a.addEventListener('timeupdate',()=>{if(a.currentTime>=to){a.pause();b.classList.remove('on');if(MP===a)MP=null}});
 a.addEventListener('ended',()=>{b.classList.remove('on');if(MP===a)MP=null});
 a.addEventListener('error',()=>{b.classList.remove('on');toast(t('noAudio'))});
 a.currentTime=from;await a.play()}catch(e){b.classList.remove('on');toast(t('noAudio'))}};
const segB=(it)=>it.media?`<button type=button class=ib title="${t('listenSrc')}" onclick="seg(this,${it.id},${it.source.audio_from},${it.source.audio_to})">${ic('headphones')}</button>`:'';
const recB=it=>it.rec?`<div class=fb id=rv${it.rec.id} style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">${ic('mic')} <span style="flex:1">${t('recAsk')}</span><button type=button class="btn s o" onclick="new Audio('/api/rec/${it.rec.token}').play().catch(()=>toast(t('noAudio')))">${ic('speaker')} ${t('listen')}</button><button type=button class="btn s g" onclick="recVote(${it.rec.id},true)">${t('recOk')}</button><button type=button class="btn s o" onclick="recVote(${it.rec.id},false)">${t('recBad')}</button></div>`:'';
window.recVote=async(id,ok)=>{try{await api('/rec/'+id+'/vote',{method:'POST',body:{ok}});const b=$('#rv'+id);if(b)b.innerHTML=ic('check')+' '+t('thanksVote')}catch(e){toast(e.message)}};
window.recDecide=async(id,ok)=>{try{await api('/rec/'+id+'/decide',{method:'POST',body:{ok}});toast(t('saved'));pages.expert()}catch(e){toast(e.message)}};
const srcH=s=>`<span class=src>${ic('scroll')} ${esc(s.doc)}</span>${s.chapter?`<span class=src>${esc(s.chapter)}</span>`:''}<span class=src>№ ${s.position}</span>${s.audio_from!=null?`<span class=src>${ic('headphones')} ${s.audio_from}–${s.audio_to} с</span>`:''}`;
const kb=id=>`<div class=kb>${[...'әөүғҡңҙҫһ'].map(c=>`<button type=button onclick="ins('${id}','${c}')">${c}</button>`).join('')}</div>`;
window.ins=(id,c)=>{const i=$('#'+id),p=i.selectionStart??i.value.length;i.value=i.value.slice(0,p)+c+i.value.slice(i.selectionEnd??p);i.focus();i.selectionStart=i.selectionEnd=p+1};
const tlang=()=>pair.split('-')[1];

let MAT='text';const MEM={};                       // выбранная вкладка и содержимое полей
window.matTab=x=>{keepMat();MAT=x;const c=$('#matc');if(c)c.outerHTML=matCards()};
function keepMat(){const g=s=>{const el=$(s);return el?el.value:undefined};
 MEM.doc=g('#sd')??MEM.doc;MEM.ch=g('#sc')??MEM.ch;MEM.txt=g('#st')??MEM.txt}
const matCards=()=>`<div class=card id=matc><h3>${ic('scissors')} ${t('materials')}</h3>
 <div class=tabs><a href="javascript:matTab('text')" class="${MAT==='text'?'on':''}">${t('mText')}</a><a href="javascript:matTab('audio')" class="${MAT==='audio'?'on':''}">${t('mAudio')}</a></div>
 <small><b>${t('step1')}</b> ${t('step1t')}</small>
 <input id=sd placeholder="${t('srcDoc')}" value="${esc(MEM.doc||'')}"><input id=sc placeholder="${t('chapter')}" value="${esc(MEM.ch||'')}">
 ${MAT==='audio'?`<small><b>${t('step2')}</b> ${t('step2a')}</small>
 <input id=af type=file accept="audio/*" hidden onchange="MEM.up='';$('#ast').textContent=this.files[0]?this.files[0].name+' \u2014 '+t('notYet'):''">
 <div class=row><button class="btn o" onclick="$('#af').click()">${t('pick')}</button><button class="btn o" onclick="upMedia()">${t('upload')}</button></div>
 <div id=ast class=mut>${MEM.up?'&#10003; '+esc(MEM.up):''}</div>
 <small><b>${t('step3')}</b> ${t('step3a')}</small>
 <textarea id=st placeholder="00:00 ${t('phAudio')}&#10;0:07 ${t('phAudio2')}">${esc(MEM.txt||'')}</textarea>
 <button type=button class="btn o" onclick="prevLines()">${ic('headphones')} ${t('checkEar')}</button><div id=prev></div>
 ${CFG.pauses||CFG.asr?`<div class=row>${CFG.pauses?`<button class="btn o" onclick="autoMark('pauses',this)">${t('doPauses')}</button>`:''}${CFG.asr?`<button class="btn o" onclick="autoMark('asr',this)">${t('doAsr')}</button>`:''}</div>
 <small class=mut>${CFG.asr?t('autoHint'):t('pausesOnly')}</small>`:`<small class=mut>${t('autoOff')}</small>`}
 <small><b>${t('step4')}</b> ${t('step4a')}</small>`:`<small><b>${t('step2')}</b> ${t('step2t')}</small>
 <textarea id=st placeholder="${t('textPh')}">${esc(MEM.txt||'')}</textarea>
 <small><b>${t('step3')}</b> ${t('step3t')}</small>
 <select id=sm><option value=sentence>${t('bySent')}</option><option value=paragraph>${t('byPara')}</option></select>`}
 <button class="btn g" onclick="slice()">${t('cut')}</button>
 <small class=mut>${t('onlyCyr')}</small>
 <button class="btn o" onclick="cleanLatin(this)">${t('cleanLatin')}</button></div>`;

// ---------- страницы ----------
const pages={
async home(){const s=await api('/me/stats'),n=s.today/s.goal,[hi,sub]=greet(),B=['first','ten','fifty','fix','streak','vocab'];
 setPage(`<div class="card hero">${mascot('happy')}<h1>${hi}, ${esc(me.name)}!</h1><p>${sub}</p><a class="btn g" href="#/translate">${t('go')} ${ic('arrow')}</a></div>
 <div class=grid><div class="card goal">${ring(n)}<div><h3>${t('today')}: ${Math.min(s.today,s.goal)} / ${s.goal}</h3><small>${s.today>=s.goal?ic('flame')+' '+t('flameOk'):`${ic('flame')} ${t('toFlame')}: ${s.goal-s.today}`}${s.today>s.goal?`<br>+${s.today-s.goal} ${t('overGoal')}`:''}</small></div></div>
 <div class=card><h3>${ic('star')} ${t('level')} ${Math.floor(me.xp/500)+1}</h3><div class=bar><i data-w="${(me.xp%500)/5}"></i></div><small><span class=cu data-v="${me.xp%500}">0</span> / 500 XP</small></div>
 <div class=card><h3>${ic('book')} <span class=cu data-v="${s.vocab}">0</span> ${t('words')}</h3><small>${ic('search')} ${t('found')}: ${s.fixes} · ${t('accuracy')} ${s.accuracy}%</small></div></div>
 <div class=card><h3>${ic('award')} ${t('ach')}</h3><div class=badges>${B.map(k=>`<figure class="${s.badges[k]?'':'no'}">${img('badge-'+k)}${t('b_'+k)}</figure>`).join('')}</div></div>
 <div class=card><h3>${t('recent')}</h3>${s.recent.length?s.recent.map(r=>`<div class=act>${r.fixed?ic('search'):r.error?ic('alert'):ic('check')} <span style="flex:1">${esc(r.text)}</span><b>+${r.xp}</b></div>`).join(''):`<div class=center>${mascot('think')}<p>${t('emptyRecent')}</p></div>`}</div>`)},
async translate(){const extra=location.hash.split('/')[2]==='more';
 const keep=(T&&T.extra&&extra)?{xp:T.xp||0,fixes:T.fixes||0,done:(T.done||0)+(T.i||0)}:{xp:0,fixes:0,done:0};
 const d=await api(`/daily?pair=${pair}${extra?'&extra=true':''}`);T={...d,pair,i:0,extra,...keep};
 if(!d.items.length){if(extra||d.done_today<d.goal)return setPage(`<div class="card center">${mascot('think')}<p>${t('noMore')}</p>${keep.done?`<p><b>+${keep.xp} XP</b> · ${t('nAnswers')}: ${keep.done}</p>`:''}<a class=btn href="#/base">${ic('base')} ${t('base')}</a> <a class="btn o" href="#/learn">${ic('learn')} ${t('learn')}</a></div>`);
  return setPage(doneCard(d.done_today,d.goal))}item()}};
const doneCard=(n,g)=>`<div class="card center">${mascot('cheer')}<h2>${t('doneTitle')} ${ic('flame')}</h2><p>${t('doneText')} (${n}/${g})</p><a class="btn g" href="#/translate/more" onclick="if(location.hash==='#/translate/more'){route();return false}">${ic('translate')} ${t('more')}</a> <a class="btn o" href="#/rating">${ic('rating')} ${t('rating')}</a></div>`;
function item(){const it=T.items[T.i];if(!it)return finish();
 setPage(`<div class="card flip plain"><div class=row><span class=chip>${ic('translate')} ${T.extra?T.done+T.i+1:`${T.i+1} / ${T.items.length}`}</span><span class=chip>${pl(pair)}</span>${T.extra?`<span class=chip>${ic('star')} ${t('extraMode')}</span>`:''}</div><div style="margin-top:.5rem">${srcH(it.source)}</div>
 <div class=frag>${spk(it.text_ba,'ba',it.id)}${segB(it)}<span>${esc(it.text_ba)}</span></div>${recB(it)}
 ${it.mode==='check'?`<div class=auto><div><small>${ic('bot')} ${t('auto')}</small>${esc(it.auto)}</div>${spk(it.auto,'tr',0,tlang())}</div><div class=row id=act><button class="btn g" onclick="sendA('confirm')">${ic('tick')} ${t('right')}</button><button class="btn" onclick="editA()">${ic('edit')} ${t('fixit')}</button></div><div id=ed></div>`:editor('')}<div id=res></div>
 <div class=foot><button class="btn s o" title="${t('reportHint')}" onclick="report(${it.id},this)">${ic('alert')} ${t('report')}</button></div></div>`)}
const editor=pre=>`<textarea id=tx placeholder="${t('mine')}">${esc(pre)}</textarea>${kb('tx')}<button class="btn g" onclick="sendA('correct')">${t('send')}</button>`;
window.editA=()=>{$('#ed').innerHTML=editor(T.items[T.i].auto);$('#act').style.display='none';$('#tx').focus()};
window.sendA=async kind=>{const it=T.items[T.i];try{const r=await api('/answer',{method:'POST',body:{fragment_id:it.id,pair,kind,text:kind==='correct'?$('#tx').value:''}});me=r.user;top_();T.xp+=r.xp;
 let cls='ok',msg=r.xp?`${ic('check')} +${r.xp} XP`:`${ic('check')} ${t('accepted')}`;
 if(r.error){cls='bad';msg=`${ic('alert')} ${t('trap')} <b>${esc(r.right||'')}</b>`;SND.bad()}
 else if(r.fixed){cls='gold';msg=`${ic('search')} ${t('fixed')}${r.xp?' +'+r.xp+' XP':''}`;T.fixes++;SND.win();confetti()}else SND.ok();
 if(!r.xp&&!r.error)msg+=`<br><small>${t('xpLater')}</small>`;if(r.status==='confirmed')msg+=`<br>${ic('party')} ${t('confirmedMsg')}`;if(r.status==='expert_review')msg+=`<br>${ic('expert')} ${t('expertMsg')}`;
 if(r.goal_reached_now){msg+=`<br>${ic('flame')} <b>${t('goalNow')}</b>`;if(r.flame_xp){msg+=` <b>+${r.flame_xp} XP</b> <small>${t('flameXp')}</small>`;T.xp+=r.flame_xp}confetti()}
 $('#res').innerHTML=`<div class="fb ${cls}">${msg}</div><button class="btn g" onclick="T.i++;item()">${t('next')} ${ic('arrow')}</button>`;document.querySelectorAll('#act button,#ed button,#tx').forEach(b=>b.disabled=true)}catch(e){toast(e.message)}};
function finish(){if(T.extra)return pages.translate();   // сверх нормы — порции идут одна за другой, без окошка
 SND.win();confetti();setPage(`<div class="card center">${mascot('cheer')}<h1>${t('bravo')} ${ic('party')}</h1><p>+${T.xp} XP · ${t('found')}: ${T.fixes}</p>${me.streak_today?`<p>${ic('flame')} ${t('flameOk')}</p>`:''}
 <a class="btn g" href="#/translate/more" onclick="if(location.hash==='#/translate/more'){route();return false}">${ic('translate')} ${t('more')}</a> <a class="btn o" href="#/home">${ic('home')} ${t('home')}</a> <a class="btn o" href="#/rating">${ic('rating')}</a></div>`)}

Object.assign(pages,{
async base(){const st=location.hash.split('/')[2]||'confirmed',q=window._q||'';const rows=await api(`/base?pair=${pair}&status=${st}&q=${encodeURIComponent(q)}`);
 const tab=(k,l)=>`<button class="${st===k?'on':''}" onclick="location.hash='#/base/${k}'">${l}</button>`,SL={confirmed:t('stConfirmed'),expert_review:t('stExpert'),collecting:t('stCollecting')};
 const how=lang==='ba'?`Һеҙҙең тәржемә — ул тауыш. Әгәр ${CFG.min_voters} һәм унан күберәк кеше яуап бирһә, ${CFG.noise}%-тан аҙ тауыш йыйған варианттар иҫәпкә алынмай. Ҡалғандары араһында ${CFG.share}% һәм унан күберәк йыйған вариант раҫлана; бер нисә көслө вариант булһа, мәсьәлә белгестәргә китә.`
  :`Ваш перевод — это голос. Когда ответили не меньше ${CFG.min_voters} человек, варианты, набравшие меньше ${CFG.noise}% голосов, не засчитываются. Среди оставшихся вариант с долей от ${CFG.share}% подтверждается; если сильных вариантов несколько — случай уходит экспертам.`;
 setPage(`<h1>${ic('base')} ${t('base')}</h1><div class=tabs>${tab('confirmed',ic('check')+' '+t('tConfirmed'))}${tab('collecting',ic('clock')+' '+t('tCollecting'))}${tab('expert_review',ic('expert')+' '+t('tDisputed'))}${tab('mine',ic('user')+' '+t('tMine'))}${['moderator','expert','admin'].includes(me.role)?`<button onclick="dl('json')">${ic('download')} JSON</button><button onclick="dl('csv')">${ic('download')} CSV</button>`:''}</div>
 <p class=credit style="text-align:left;margin:.2rem 0 .8rem"><b>${t('howTitle')}:</b> ${how}</p>
 <input placeholder="${t('search')}" value="${esc(q)}" onchange="window._q=this.value;route()">`+(rows.length?rows.map(r=>`<div class=card><div>${srcH(r.source)}</div><div class=frag style="font-size:1.35rem">${spk(r.text_ba,'ba',r.id)}<span>${esc(r.text_ba)}</span></div>
 <div class=auto style="font-size:1.1rem;animation:none"><div><small>${pl(pair)} · ${r.mine?t('yourVar'):r.expert?ic('class')+' '+t('expertMark'):t('leading')+' · '+t('votes')+': '+r.confirmed}</small>${esc(r.translation)}</div>${spk(r.translation,'tr',0,tlang())}</div>
 ${r.variants&&r.variants.length>1?`<small>${t('allVars')}:</small>`+r.variants.map(v=>`<div class=var><span>${esc(v[0])}</span><span class=pct style="width:${Math.max(4,v[2]||0)/2}%"></span><b>${v[2]??''}% · ${v[1]} ${ic('users')}</b></div>`).join(''):''}
 <span class="chipst st-${r.status}">${SL[r.status]||r.status}</span>${r.mine&&r.final&&r.status==='confirmed'?` <small>${t('result')}: ${esc(r.final)}</small>`:''} ${['teacher','moderator','expert','admin'].includes(me.role)?`<button class="btn s o" onclick="rec(this,${r.id})">${ic('mic')} ${t('recVoice')}</button> `:''}<button class="btn s o" onclick="cm(${r.id})">${ic('comment')} ${t('comments')} (${r.comments})</button><div id=c${r.id}></div></div>`).join(''):`<div class="card center">${mascot('think')}<p>${t('emptyBase')}</p></div>`))},
async rating(){const [,,sc='all',pe='all',mt='points']=location.hash.split('/'),d=await api(`/rating?scope=${sc}&period=${pe}&metric=${mt}`);
 const L=(k,a,b)=>`<a href="#/rating/${k==='s'?a:sc}/${k==='p'?a:pe}/${k==='m'?a:mt}" class="${(k==='s'?sc:k==='p'?pe:mt)===a?'on':''}">${b}</a>`;
 setPage(`<h1>${ic('rating')} ${t('rating')}</h1><div class=tabs>${[['all','sAll'],['school','sSchool'],['class','sClass'],['schools','sSchools']].map(x=>L('s',x[0],t(x[1]))).join('')}</div><div class=tabs>${[['day','pDay'],['week','pWeek'],['month','pMonth'],['year','pYear'],['all','pAll']].map(x=>L('p',x[0],t(x[1]))).join('')}</div><div class=tabs>${[['points','mPoints'],['vocab','mVocab'],['fixes','mFixes'],['clean','mClean']].map(x=>L('m',x[0],t(x[1]))).join('')}</div>`+
 (d.need_school?`<div class=card>${t('needSchool')}</div>`:d.rows.length?d.rows.map((r,i)=>`<div class="rk ${r.me?'me':''}" style="animation-delay:${i*.05}s"><b class=n>${r.rank<=3?`<span class="medal m${r.rank}">${r.rank}</span>`:r.rank}</b><span>${esc(r.name)} <small>${esc(r.sub)}</small></span><span class=v>${r.value}</span></div>`).join(''):`<div class="card center">${mascot('think')}<p>${t('noData')}</p></div>`))},
async class(){const r=await api('/teacher/report');setPage(`<h1>${ic('class')} ${t('class')}</h1><div class=card><h3>${t('report')}</h3>${r.length?`<div style="overflow-x:auto"><table class=t><tr><th align=left>${t('student')}<th>${t('level')}<th>${t('answers')}<th>${t('fixesS')}<th>${t('errorsS')}<th>XP<th>${t('streak')}</tr>${r.map(x=>`<tr><td>${esc(x.name)}<td align=center><b>${x.level||1}</b><td align=center>${x.answers}<td align=center>${x.fixes}<td align=center>${x.errors}<td align=center>${x.xp}<td align=center>${x.streak}</tr>`).join('')}</table></div>`:`<p>${me.school&&me.class_name?t('noStudents'):t('needClass')}</p>`}</div>
 <div class=card><h3>${ic('key')} ${t('invite')}</h3><p><small>${t('inviteHint')}</small></p><div id=inv><button class="btn g" onclick="mkInvite()">${t('makeInvite')}</button></div>${r.length?`<button class="btn o" onclick="dlReport()">${ic('download')} ${t('csv')}</button>`:''}</div>
 ${matCards()}`)},
async expert(){const q=await api('/expert/queue'),rq=await api('/expert/recs'),ex=['expert','admin'].includes(me.role);setPage(`<h1>${ic('expert')} ${t('expert')}</h1>`+(rq.length?`<div class=card><h3>${ic('mic')} ${t('recQueue')}</h3><small>${t('recQueueHint')}</small>${rq.map(r=>`<div class=act><button type=button class=ib onclick="new Audio('/api/rec/${r.token}').play()">${ic('speaker')}</button><span style="flex:1">${esc(r.text_ba)}<br><small>${esc(r.author)} · ${t('recOk')}: ${r.yes} · ${t('recBad')}: ${r.no}</small></span>${r.status==='expert'?(ex?`<button class="btn s g" onclick="recDecide(${r.id},true)">${t('accept')}</button><button class="btn s o" onclick="recDecide(${r.id},false)">${t('reject')}</button>`:`<b>${t('waitExpert')}</b>`):`<b>${t('onVote')} ${r.yes+r.no}/${r.need}</b>`}</div>`).join('')}</div>`:'')+(q.length?q.map(x=>`<div class=card>${srcH(x.source)} <span class=src>${pl(x.pair)}</span><div class=frag style="font-size:1.35rem">${spk(x.text_ba,'ba',x.id)}<span>${esc(x.text_ba)}</span></div>${x.variants.map(v=>`<div class=act><span style="flex:1">${esc(v[0])}</span><b>${v[2]}% · ${v[1]} ${ic('users')}</b>${ex?`<button class="btn s g" data-f="${x.id}" data-p="${x.pair}" data-t="${esc(v[0])}" onclick="decide(this.dataset.f,this.dataset.p,this.dataset.t)">${t('accept')}</button>`:''}</div>`).join('')}</div>`).join(''):`<div class="card center">${mascot('happy')}<p>${t('noDisputes')}</p></div>`))},
async admin(){const us=await api('/admin/users');setPage(`<h1>${ic('admin')} ${t('admin')}</h1><div class=card><h3>${t('users')}</h3><div style="overflow-x:auto"><table class=t><tr><th align=left>${t('nameCol')}<th align=left>${t('email')}<th>${t('roleCol')}<th>${t('blockCol')}</tr>${us.map(x=>`<tr><td>${esc(x.name)}<td>${esc(x.email)}<td><select onchange="setRole(${x.id},this.value)">${Object.keys(ROLES).map(r=>`<option value=${r} ${r===x.role?'selected':''}>${rl(r)}</option>`).join('')}</select><td align=center><input type=checkbox style="width:auto;margin:0" ${x.blocked?'checked':''} onchange="blockU(${x.id},this.checked)"></tr>`).join('')}</table></div></div>
 ${matCards()}
 <div class=card><h3>${t('addSchool')}</h3><input id=ac placeholder="${t('cityOr')}"><input id=an placeholder="${t('schoolName')}"><button class="btn g" onclick="addSchool()">${t('add')}</button></div>`)},
async settings(){setPage(`<h1>${ic('settings')} ${t('settings')}</h1><div class=card><h3>${t('language')}</h3><button class="btn ${lang==='ru'?'g':'o'}" onclick="setLang('ru')">Русский</button> <button class="btn ${lang==='ba'?'g':'o'}" onclick="setLang('ba')">Башҡортса</button>
 <h3>${t('pairl')}</h3><select onchange="setPair(this.value)">${Object.keys(PAIRS).map(k=>`<option value=${k} ${k===pair?'selected':''}>${pl(k)}</option>`).join('')}</select>
 <h3>${ic('speaker')} ${t('sound')}</h3><button class="btn o" onclick="ls.set('snd',ls.get('snd')==='0'?'1':'0');SND.ok();toast(ls.get('snd')==='0'?t('soundOff'):t('soundOn'))">${t('toggle')}</button></div>
 <div class=card><h3>${ic('school')} ${t('school')}</h3><p>${esc(me.school||t('notSelected'))} ${esc(me.class_name)}</p>${['teacher','admin'].includes(me.role)?`<small class=mut>${t('teacherSchool')}</small><div id=sb></div>`:`<small class=mut>${t('schoolByCode')}</small>`}<h3>${t('classCodeH')}</h3><div class=row><input id=cc style="flex:1;text-transform:uppercase" maxlength=12 placeholder="${t('classCode')}"><button class="btn" onclick="joinClass()">${t('join')}</button></div></div>
 ${CFG.bot?`<div class=card><h3>${ic('send')} ${t('tg')}</h3><p id=tgs>${t('tgHint')}</p><button class="btn g" onclick="tgLink()">${t('tgLink')}</button> <a class="btn o" href="https://t.me/${esc(CFG.bot)}" target=_blank rel=noopener>${t('tgOpen')}</a></div>`:''}
 <div class=card><b>${esc(me.email)}</b> <span class=role>${rl(me.role)}</span><br><br><button class="btn o" onclick="out()">${t('logout')}</button> <button class="btn r" onclick="api('/logout-all',{method:'POST'}).then(out)">${t('logoutAll')}</button></div>
 <p class=credit>${t('credit')}</p>`);if(['teacher','admin'].includes(me.role))setTimeout(()=>schoolBox('sb',true),300);if(CFG.bot)api('/tg/status').then(r=>{if(r.linked&&$('#tgs'))$('#tgs').innerHTML=ic('check','ic ok')+' '+t('tgLinked')}).catch(()=>{})}});

// ---------- страницы из шапки: серия, опыт, профиль ----------
Object.assign(pages,{
async streak(){const d=await api('/me/stats'),left=Math.max(0,d.goal-d.today);
 setPage(`<h1>${ic('flame','ic h1i')} ${t('streak')}</h1>
 <div class="card hero">${mascot(d.today>=d.goal?'cheer':'happy')}<h2>${d.streak} ${t('days')}</h2>
 <p>${d.today>=d.goal?t('flameOk'):`${t('todayLeft')}: ${left}`}</p>
 ${d.today>=d.goal?'':`<a class="btn g" href="#/translate">${ic('translate')} ${t('keepGoing')}</a>`}</div>
 ${d.can_fix?`<div class="card center">${mascot('sad')}<h3>${ic('flame')} ${t('fixTitle')}</h3><p>${t('fixText').replace('{n}',d.lost_streak).replace('{cost}',d.fix_cost)}</p>${me.xp>=d.fix_cost?`<button class="btn g" onclick="fixStreak()">${ic('flame')} ${t('fixBtn').replace('{cost}',d.fix_cost)}</button>`:`<p><small>${t('fixNoXp').replace('{cost}',d.fix_cost)}</small></p>`}</div>`:''}
 <div class=grid><div class=card><h3>${ic('award')} ${t('streakBest')}</h3><p class=big><span class=cu data-v="${d.best_streak}">0</span> ${t('days')}</p></div>
 <div class=card><h3>${ic('check')} ${t('daysDone')}</h3><p class=big><span class=cu data-v="${d.days_done}">0</span></p></div></div>
 <div class=card><h3>${t('last28')}</h3><div class=cal>${d.days.map(x=>`<i class="${x.goal?'g':x.n?'p':''}" title="${x.d}: ${x.n}"></i>`).join('')}</div>
 <p class=credit style="text-align:left">${t('streakRule').replace('{goal}',d.goal)}</p></div>`)},
async xp(){const d=await api('/me/stats'),lv=Math.floor(me.xp/500)+1,inLv=me.xp%500,R=[['xpR1','+10'],['xpR2','+25'],['xpR3','0'],['xpR6','+15'],['xpR4','+2'],['xpR5','+3']];
 setPage(`<h1>${ic('gem','ic h1i')} ${t('xp')}</h1>
 <div class="card hero">${mascot('happy')}<h2>${t('level')} ${lv}</h2><div class=bar style="max-width:22rem"><i data-w="${inLv/5}"></i></div>
 <p><span class=cu data-v="${inLv}">0</span> / 500 XP · ${t('toNext')}: ${500-inLv}</p></div>
 <div class=grid><div class=card><h3>${ic('gem')} ${t('xpTotal')}</h3><p class=big><span class=cu data-v="${me.xp}">0</span> XP</p></div>
 <div class=card><h3>${t('xpFrom')}</h3><div class=act><span style="flex:1">${t('xpTr')}</span><b>${d.xp_translate} XP</b></div><div class=act><span style="flex:1">${t('xpFl')} ${ic('flame')}</span><b>${d.xp_flame||0} XP</b></div><div class=act><span style="flex:1">${t('xpLe')}</span><b>${d.xp_learn} XP</b></div></div></div>
 <div class=card><h3>${t('howXp')}</h3>${R.map(([k,v])=>`<div class=act><span style="flex:1">${t(k)}</span><b>${v} XP</b></div>`).join('')}<p class=credit style="text-align:left">${t('xpNote')}</p></div>`)},
async profile(){const d=await api('/me/stats'),B=['first','ten','fifty','fix','streak','vocab'];
 setPage(`<h1>${ic('user','ic h1i')} ${t('profile')}</h1>
 <div class="card hero">${mascot('happy')}<h2>${esc(me.name)}</h2>
 <p>${ic('school')} ${esc(me.school||t('noSchool'))} ${esc(me.class_name)}<br>${ic('user')} ${t('roleIs')}: ${rl(me.role)} · ${t('since')} ${esc(d.since)}</p>
</div>
 <div class=grid>
 <div class=card><h3>${ic('translate')} ${t('nAnswers')}</h3><p class=big><span class=cu data-v="${d.answers}">0</span></p><small>${t('nConfirm')}: ${d.confirms} · ${t('nFix')}: ${d.corrections}</small></div>
 <div class=card><h3>${ic('book')} ${t('mVocab')}</h3><p class=big><span class=cu data-v="${d.vocab}">0</span></p><small>${t('accuracy')}: ${d.accuracy}%</small></div>
 <div class=card><h3>${ic('search')} ${t('nFound')}</h3><p class=big><span class=cu data-v="${d.fixes}">0</span></p><small>${t('nErr')}: ${d.errors}</small></div></div>
 <div class=card><h3>${ic('award')} ${t('ach')}</h3><div class=badges>${B.map(k=>`<figure class="${d.badges[k]?'':'no'}">${img('badge-'+k)}${t('b_'+k)}</figure>`).join('')}</div></div>`)}});

// ---------- «Интересное»: факты, вопросы с подвохом, сборка предложений, контрольная ----------
let L={};
pages.learn=async()=>{const sub=location.hash.split('/')[2]||'facts';
 const tab=(k,l)=>`<a href="#/learn/${k}" class="${sub===k?'on':''}">${t(l)}</a>`,head=`<h1>${ic('learn','ic h1i')} ${t('learn')}</h1><div class=tabs>${tab('facts','lFacts')}${tab('quiz','lQuiz')}${tab('build','lBuild')}${tab('test','lTest')}</div>`;
 if(sub==='facts'){const d=await api('/learn/facts');return setPage(head+`<div class="card hero fact">${mascot('think')}<small class=kick>${t('factDay')}</small><h2>${ic(d.fact_of_day.icon,'ic hi')} ${esc(d.fact_of_day.title)}</h2><p>${esc(d.fact_of_day.text)}</p></div><div class="grid facts">${d.facts.map(f=>`<div class=card><h3><span class=fi>${ic(f.icon)}</span>${esc(f.title)}</h3><p>${esc(f.text)}</p></div>`).join('')}</div>`)}
 if(sub==='quiz'){L={items:await api('/learn/quiz'),i:0,score:0,mode:'quiz',head};return lStep()}
 if(sub==='build'){L={items:[await api('/learn/build')],i:0,score:0,mode:'build',head,endless:true};return lStep()}
 if(sub==='test'){if(location.hash.split('/')[3]!=='go')return setPage(head+`<div class="card center">${mascot('happy')}<h2>${t('lTest')}</h2><p>${t('testIntro')}</p><a class="btn g" href="#/learn/test/go">${t('start')}</a></div>`);L={items:await api('/learn/test'),i:0,score:0,mode:'test',head};return lStep()}};
function lStep(){const it=L.items[L.i];if(!it)return lDone();const n=L.endless?'':`<span class=chip>${t('question')} ${L.i+1} / ${L.items.length}</span> `;
 if(it.kind==='quiz')return setPage(L.head+`<div class="card flip plain">${n}<h2 style="margin-top:.8rem">${esc(it.q)}</h2><div class=opts>${it.options.map((o,k)=>`<button class=opt onclick="lQuiz(${k},this)">${esc(o)}</button>`).join('')}</div><div id=res></div></div>`);
 L.picked=[];setPage(L.head+`<div class="card flip plain">${n}<p><small>${t('buildHint')}</small></p><p>${t('translateIt')}</p><h2>${esc(it.ru)}</h2><div id=line class=line></div><div id=tiles class=tiles>${it.tiles.map((w,k)=>`<button class=tile data-k=${k} onclick="lPick(${k})">${esc(w)}</button>`).join('')}</div><div class=row><button class="btn g" id=chk onclick="lBuild()">${t('check')}</button><button class="btn o" onclick="lClear()">${t('clear')}</button></div><div id=res></div></div>`)}
window.lMore=async()=>{try{L.items=[await api('/learn/build')];L.i=0;lStep()}catch(e){toast(e.message)}};
window.lQuiz=async(k,b)=>{const it=L.items[L.i];document.querySelectorAll('.opt').forEach(x=>x.disabled=true);try{const r=await api('/learn/quiz/check',{method:'POST',body:{id:it.id,choice:k}});
 document.querySelectorAll('.opt')[r.right].classList.add('good');if(!r.correct)b.classList.add('badc');if(r.correct){L.score++;SND.ok()}else SND.bad();if(r.xp){me.xp+=r.xp;top_()}
 $('#res').innerHTML=`<div class="fb ${r.correct?'ok':'bad'}">${r.correct?ic('check')+' '+t('rightAns'):ic('alert')+' '+t('wrongAns')} ${esc(r.explain)}${r.xp?` <b>+${r.xp} XP</b>`:''}</div>`+(L.mode==='quiz'&&L.i===L.items.length-1?`<button class="btn g" onclick="L.i++;lStep()">${t('resultT')} ${ic('arrow')}</button>`:`<button class="btn g" onclick="L.i++;lStep()">${t('next')} ${ic('arrow')}</button>`)}catch(e){toast(e.message)}};
window.lPick=k=>{const b=document.querySelector(`.tile[data-k="${k}"]`);if(b.parentNode.id==='tiles'){$('#line').append(b);L.picked.push(k)}else{$('#tiles').append(b);L.picked=L.picked.filter(x=>x!==k)}SND.pop()};
window.lClear=()=>{document.querySelectorAll('#line .tile').forEach(b=>$('#tiles').append(b));L.picked=[]};
window.lBuild=async()=>{const it=L.items[L.i];if(!L.picked.length)return;try{const r=await api('/learn/build/check',{method:'POST',body:{id:it.id,words:L.picked.map(k=>it.tiles[k])}});
 document.querySelectorAll('.tile').forEach(x=>x.disabled=true);$('#chk').disabled=true;if(r.correct){L.score++;SND.ok()}else SND.bad();if(r.xp){me.xp+=r.xp;top_()}
 $('#res').innerHTML=`<div class="fb ${r.correct?'ok':'bad'}">${r.correct?ic('check')+' '+t('rightAns'):ic('alert')+' '+t('wrongAns')+' '+t('correctIs')} <b>${esc(r.answer)}</b>${r.xp?` <b>+${r.xp} XP</b>`:''}</div>`+(L.endless?`<button class="btn g" onclick="lMore()">${t('next')} ${ic('arrow')}</button>`:`<button class="btn g" onclick="L.i++;lStep()">${t('next')} ${ic('arrow')}</button>`)}catch(e){toast(e.message)}};
function lDone(){const n=L.items.length,p=n?L.score/n:0,g=p>=.9?'grade5':p>=.7?'grade4':p>=.5?'grade3':'grade2';if(p>=.7){SND.win();confetti()}
 setPage(L.head+`<div class="card center">${mascot(p>=.5?'cheer':'sad')}<h2>${t('resultT')}: ${L.score} / ${n}</h2><p>${t(g)}</p><p><small>${t('xpCap')}</small></p><a class="btn g" href="#/learn/${L.mode==='test'?'test':'quiz'}" onclick="route();return false">${t('again')}</a> <a class="btn o" href="#/learn/facts">${t('lFacts')}</a></div>`)}

// ---------- действия ----------
window.fixStreak=async()=>{try{const r=await api('/me/streak-fix',{method:'POST'});me=r.user;top_();SND.win();confetti();toast(t('fixDone'));route()}catch(e){toast(e.message)}};
window.setPair=async v=>{const old=pair;pair=v;ls.set('pair',v);
 try{me=await api('/me/pair',{method:'PATCH',body:{pair:v}});toast(t('saved'))}catch(e){pair=old;ls.set('pair',old);toast(e.message)}};
window.setLang=l=>{lang=l;ls.set('lang',l);document.documentElement.lang=l;if(me){chrome(location.hash.slice(2).split('/')[0]||'home');route()}else authView(authView.m||'login')};
window.out=()=>{api('/logout',{method:'POST'}).catch(()=>{});ls.del('tok');tok=null;me=null;location.hash='#/auth';route()};
window.cm=async id=>{const b=$('#c'+id),l=await api(`/fragments/${id}/comments`);b.innerHTML=l.map(c=>`<div class=cm><b>${esc(c.author)}</b><span class=role>${rl(c.role)} · ${ic('star')} ${t('lvlShort')} ${c.level||1}</span>${esc(c.text)}${c.mine||['moderator','expert','admin'].includes(me.role)?` <a href=# onclick="delCm(${c.id},${id});return false">${ic('trash')}</a>`:''}</div>`).join('')+`<input id=ci${id} placeholder="${t('write')}"><button class="btn s" onclick="sendCm(${id})">${t('send')}</button>`};
window.sendCm=async id=>{try{await api(`/fragments/${id}/comments`,{method:'POST',body:{text:$('#ci'+id).value}});SND.pop();cm(id)}catch(e){toast(e.message)}};
window.delCm=async(c,id)=>{await api('/comments/'+c,{method:'DELETE'});cm(id)};
window.setRole=async(id,r)=>{try{await api('/admin/users/'+id,{method:'PATCH',body:{role:r}});toast(t('roleChanged'))}catch(e){toast(e.message);route()}};
window.blockU=async(id,b)=>{try{await api('/admin/users/'+id,{method:'PATCH',body:{blocked:b}});toast(b?t('blocked'):t('unblocked'))}catch(e){toast(e.message);route()}};
window.addSchool=async()=>{try{await api('/admin/schools',{method:'POST',body:[{city:$('#ac').value,name:$('#an').value}]});toast(t('schoolAdded'));SND.ok()}catch(e){toast(e.message)}};
window.dl=async f=>{try{const r=await fetch(`/api/v1/export?pair=${pair}&format=${f}`,{headers:{Authorization:'Bearer '+tok}});const b=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=`tamga_${pair}.${f}`;a.click()}catch(e){toast(e.message)}};
window.decide=async(f,p,tr)=>{try{await api(`/expert/${f}/decide`,{method:'POST',body:{pair:p,translation:tr}});SND.ok();toast(t('decided'));route()}catch(e){toast(e.message)}};
window.upMedia=async()=>{keepMat();const f=$('#af').files[0],d=$('#sd').value.trim();
 if(!f||!d)return toast(t('needFile'));
 if(f.size>60e6)return toast(t('tooBig'));
 $('#ast').textContent=t('working');
 try{const r=await fetch('/api/admin/audio?doc='+encodeURIComponent(d),{method:'POST',headers:{'Content-Type':f.type||'audio/mpeg',Authorization:'Bearer '+tok},body:f});
  const o=await r.json();if(!r.ok)throw new Error(o.detail||t('oops'));
  MEM.up=f.name;$('#ast').textContent='\u2713 '+f.name+' — '+t('onServer');SND.ok();toast(t('uploaded'));return true}
 catch(e){$('#ast').textContent='';toast(e.message||t('oops'));return false}};
window.autoMark=async(mode,b)=>{keepMat();const doc=$('#sd').value.trim();
 if(!doc)return toast(t('needDoc'));
 if(mode==='pauses'&&$('#st').value.trim().length<10)return toast(t('needText'));
 const old=b.innerHTML;b.disabled=true;b.textContent=t('working');
 try{if(!MEM.up&&$('#af').files[0]&&!await upMedia()){b.disabled=false;b.innerHTML=old;return}   // файл выбран, но не отправлен — отправим сами
  const {job}=await api('/admin/transcribe',{method:'POST',body:{doc,mode,text:$('#st').value}});
  for(let i=0;i<1200;i++){await new Promise(r=>setTimeout(r,1500));
   const s=await api('/admin/transcribe/'+job);
   if(s.state==='run'){const sec=Math.round((i+1)*1.5);b.textContent=(s.stage==='load'?t('loadingModel'):t('working'))+(s.progress>.01?` ${Math.round(s.progress*100)}%`:'')+` · ${sec>=60?Math.floor(sec/60)+' '+t('minS')+' ':''}${sec%60} ${t('secS')}`;continue}
   if(s.state==='error'){if(s.raw)$('#ast').textContent='⚠ '+s.raw;throw new Error(s.error)}
   $('#st').value=s.text;MEM.txt=s.text;SND.ok();toast(`${t('marked')}: ${s.lines}`);if(s.note)$('#ast').textContent='⚠ '+s.note;return}
  throw new Error(t('tooLongJob'))}
 catch(e){toast(e.message)}finally{b.disabled=false;b.innerHTML=old}};
window.cleanLatin=async b=>{const o=b.innerHTML;b.disabled=true;b.textContent=t('working');
 try{const r=await api('/admin/cleanup',{method:'POST'});toast(`${t('hidden')}: ${r.hidden}`)}
 catch(e){toast(e.message)}finally{b.disabled=false;b.innerHTML=o}};
let PA=null;
window.prevLines=async()=>{keepMat();const doc=$('#sd').value.trim();if(!doc)return toast(t('needDoc'));
 try{const {file}=await api('/admin/media-info?doc='+encodeURIComponent(doc));
  const rows=[];for(const l of $('#st').value.split('\n')){const m=l.match(/^\s*\[?(\d{1,2}):(\d{2})(?::(\d{2}))?\]?\s*[-–—]?\s*(.+?)\s*$/);if(m)rows.push([m[3]?+m[1]*3600+ +m[2]*60+ +m[3]:+m[1]*60+ +m[2],m[4]])}
  if(!rows.length)return toast(t('needText'));
  rows.sort((a,b)=>a[0]-b[0]);
  $('#prev').innerHTML=`<small class=mut>${t('checkEarHint')}</small>`+rows.map((r,i)=>`<div class=act><button type=button class=ib onclick="playSrc(this,'${file}',${r[0]},${i+1<rows.length?rows[i+1][0]:r[0]+15})">${ic('speaker')}</button><span style="flex:1"><small>${Math.floor(r[0]/60)}:${String(r[0]%60).padStart(2,'0')}</small> ${esc(r[1])}</span></div>`).join('')}
 catch(e){toast(e.message)}};
window.playSrc=(b,file,from,to)=>{if(PA){PA.pause();PA=null;document.querySelectorAll('#prev .ib.on').forEach(x=>x.classList.remove('on'))}
 const a=new Audio('/api/msrc/'+file);PA=a;b.classList.add('on');
 a.addEventListener('loadedmetadata',()=>{a.currentTime=from;a.play().catch(()=>{})});
 a.addEventListener('timeupdate',()=>{if(a.currentTime>=to){a.pause();b.classList.remove('on')}});
 a.addEventListener('error',()=>{b.classList.remove('on');toast(t('noAudio'))})};
window.slice=async()=>{keepMat();try{const r=await api('/admin/slice',{method:'POST',body:{text:$('#st').value,source_doc:$('#sd').value,chapter:$('#sc').value,mode:MAT==='audio'?'audio':$('#sm').value}});toast(`${t('created')}: ${r.fragments}`+(r.skipped?` · ${t('skipped')}: ${r.skipped}`:''));SND.ok()}catch(e){toast(e.message)}};

window.mkInvite=async()=>{try{const r=await api('/teacher/invite',{method:'POST'});$('#inv').innerHTML=`<p style="font-size:2rem;letter-spacing:.2em;margin:.3rem 0"><b>${esc(r.code)}</b> <small style="font-size:1rem;letter-spacing:0">${esc(r.class_name)}</small></p>${r.bot?`<small>Telegram: <a href="https://t.me/${esc(r.bot)}?start=${esc(r.code)}" target=_blank rel=noopener>t.me/${esc(r.bot)}?start=${esc(r.code)}</a></small>`:''}`;SND.ok()}catch(e){toast(e.message)}};
window.dlReport=async()=>{try{const r=await fetch('/api/teacher/report?format=csv',{headers:{Authorization:'Bearer '+tok}});const b=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='class_report.csv';a.click()}catch(e){toast(e.message)}};
window.joinClass=async()=>{try{me=await api('/me/class-code',{method:'POST',body:{code:$('#cc').value}});top_();SND.ok();toast(t('joined')+' '+me.class_name);route()}catch(e){toast(e.message)}};
window.tgLink=async()=>{try{const r=await api('/tg/link-code',{method:'POST'});if(r.link)location.href=r.link}catch(e){toast(e.message)}};
window.report=async(id,btn)=>{btn.disabled=true;try{const r=await api(`/fragments/${id}/report`,{method:'POST'});toast(r.hidden?t('reportedHidden'):t('reported'));SND.pop();
 T.items=T.items.filter(x=>x.id!==id);if(T.i>=T.items.length)finish();else item()}catch(e){toast(e.message);btn.disabled=false}};
let recorder=null;
window.rec=async(btn,id)=>{if(recorder){recorder.stop();return}
 try{const st=await navigator.mediaDevices.getUserMedia({audio:true}),ch=[];recorder=new MediaRecorder(st);recorder.ondataavailable=e=>ch.push(e.data);
  recorder.onstop=async()=>{st.getTracks().forEach(x=>x.stop());recorder=null;btn.innerHTML=ic('mic')+' '+t('recVoice');btn.classList.remove('r');
   try{const r=await fetch(`/api/fragments/${id}/audio`,{method:'POST',headers:{Authorization:'Bearer '+tok},body:new Blob(ch,{type:'audio/webm'})});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||t('oops'));toast(t('recSaved'));SND.ok()}catch(e){toast(e.message)}};
  recorder.start();btn.innerHTML=ic('mic')+' '+t('recStop');btn.classList.add('r');setTimeout(()=>recorder&&recorder.stop(),30000)}catch{toast(t('noMic'))}};
// ---------- школы: город → школа → класс и буква ----------
window.schoolBox=async(id,save)=>{const b=$('#'+id),c=await api('/schools/cities');b.innerHTML=`<select id=scy onchange="loadSch()"><option value="">${t('city')}</option>${c.map(x=>`<option>${esc(x)}</option>`).join('')}</select><select id=ss><option value="">${t('school')}</option></select><div class=row><select id=sg>${[...Array(11)].map((_,i)=>`<option>${i+1}</option>`).join('')}</select><select id=sl>${[...'АБВГДЕЖЗИК'].map(x=>`<option>${x}</option>`).join('')}</select></div>${save?`<button class="btn g" onclick="saveSchool()">${t('save')}</button>`:''}`};
window.loadSch=async()=>{const l=await api('/schools?city='+encodeURIComponent($('#scy').value));$('#ss').innerHTML=`<option value="">${t('school')}</option>`+l.map(x=>`<option value="${x.id}">${esc(x.name)}</option>`).join('')};
window.saveSchool=async()=>{try{me=await api('/me/school',{method:'PATCH',body:{school_id:+$('#ss').value||null,grade:+$('#sg').value,letter:$('#sl').value}});top_();SND.ok();toast(t('saved'));route()}catch(e){toast(e.message)}};

// ---------- вход и регистрация с кодом на почту ----------
function authView(m,info=''){authView.m=m;A.innerHTML=`<div class=auth>${mascot(m==='code'?'think':'happy')}<h1>Тамға</h1><p class=tag>${t('tagline')}</p><div class="card plain" style="text-align:left"><div class=tabs><a href=# class="${m==='login'?'on':''}" onclick="authView('login');return false">${t('login')}</a><a href=# class="${m!=='login'?'on':''}" onclick="authView('reg');return false">${t('reg')}</a></div>
 ${m==='login'?`<input id=e type=email autocomplete=email placeholder="${t('email')}"><input id=pw type=password autocomplete=current-password placeholder="${t('passIn')}" onkeydown="if(event.key==='Enter')doLogin()"><button class="btn g" onclick="doLogin()">${t('login')}</button>`
 :m==='reg'?`<input id=n placeholder="${t('name')}"><input id=e type=email autocomplete=email placeholder="${t('email')}"><input id=pw type=password autocomplete=new-password placeholder="${t('pass')}"><input id=ccode maxlength=12 style="text-transform:uppercase" placeholder="${t('classCode')}"><button class="btn g" onclick="doStart()">${t('send')}</button>`
 :`<p>${info}</p><input id=cd inputmode=numeric maxlength=6 placeholder="${t('code')}" onkeydown="if(event.key==='Enter')doConfirm()"><button class="btn g" onclick="doConfirm()">OK</button><button class="btn o" onclick="doResend()">${t('resend')}</button>`}
 <p id=er class=err></p></div><div class=lang><button class="${lang==='ru'?'on':''}" onclick="setLang('ru')">Русский</button><button class="${lang==='ba'?'on':''}" onclick="setLang('ba')">Башҡортса</button></div></div>`;
 fitAuth()}
// подгонка окна входа под высоту экрана: на большом мониторе крупнее, на низком ноутбуке мельче,
// но всегда целиком — вместе с кнопкой и переключателем языка
function fitAuth(){const a=$('.auth');if(!a)return;
 const im=a.querySelector('img.mascot');                     // картинка ещё не загрузилась — высота неизвестна
 if(im&&!im.complete){im.addEventListener('load',fitAuth,{once:true});im.addEventListener('error',fitAuth,{once:true})}
 a.style.transition='none';                                  // замер делаем в натуральную величину и без анимации
 a.style.setProperty('--az','1');a.style.minHeight='0';
 const r=a.getBoundingClientRect();a.style.minHeight='';
 if(!r.height||!r.width){a.style.transition='';return}
 const k=+Math.max(.62,Math.min((innerHeight-8)/r.height,(innerWidth-8)/r.width,1.25)).toFixed(3);
 a.style.setProperty('--az',fitAuth.k||k);                   // стартуем с прежнего масштаба
 a.offsetHeight;a.style.transition='';                       // и плавно переезжаем к новому
 a.style.setProperty('--az',k);fitAuth.k=k}
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fitAuth);
addEventListener('resize',()=>{clearTimeout(fitAuth.t);fitAuth.t=setTimeout(fitAuth,120)});
window.authView=authView;const err=e=>{$('#er').textContent=e.message;fitAuth()};
window.doLogin=async()=>{try{const r=await api('/login',{method:'POST',body:{email:$('#e').value,password:$('#pw').value}});tok=r.token;ls.set('tok',tok);me=null;SND.ok();location.hash='#/home';route()}catch(e){err(e)}};
let pend='';window.doStart=async()=>{try{pend=$('#e').value;const r=await api('/register/start',{method:'POST',body:{name:$('#n').value,email:pend,password:$('#pw').value,class_code:$('#ccode').value.trim()}});authView('code',`${t('codeSent')} <b>${esc(pend)}</b>`+(r.dev_code?`<br><small>${t('devCode')} <b>${r.dev_code}</b></small>`:''))}catch(e){err(e)}};
window.doResend=async()=>{try{const r=await api('/register/resend',{method:'POST',body:{email:pend}});toast(r.dev_code?t('devCode')+' '+r.dev_code:t('newMail'));SND.pop()}catch(e){err(e)}};
window.doConfirm=async()=>{try{const r=await api('/register/confirm',{method:'POST',body:{email:pend,code:$('#cd').value}});tok=r.token;ls.set('tok',tok);me=null;SND.win();confetti();location.hash='#/home';route()}catch(e){err(e)}};

// ---------- запуск ----------
async function route(){document.documentElement.lang=lang;const h=location.hash.slice(2).split('/')[0]||'home';
 if(h==='tg'){const code=location.hash.split('/')[2]||'';A.innerHTML=`<div class=auth>${mascot('think')}<p>${t('tgLogin')}</p></div>`;try{const r=await api('/tg/login',{method:'POST',body:{code}});tok=r.token;ls.set('tok',tok);me=null;location.replace('#/home');return route()}catch(e){tok=null;ls.del('tok');authView('login');return err(e)}}if(!tok){A.innerHTML='';return authView('login')}
 try{if(!me){me=await api('/me');if(me.pair){pair=me.pair;ls.set('pair',pair)}}shell();const pg=pages[h]&&can(h)?h:'home';chrome(pg);await pages[pg]()}catch(e){if(tok&&$('#pg'))setPage(`<div class="card center">${mascot('sad')}<p>${esc(e.message)}</p></div>`)}}
api('/config').then(c=>{CFG=c;if(me&&location.hash.startsWith('#/settings'))route()}).catch(()=>{});
if('speechSynthesis' in window)try{speechSynthesis.getVoices()}catch{}
addEventListener('hashchange',route);route();
