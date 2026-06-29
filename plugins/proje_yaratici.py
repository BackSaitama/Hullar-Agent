def calistir():
    # Kullanıcının proje türünü ve ayrıntılarını al
    proje_tur = input("Proje türü (web sitesi, uygulama, oyun vb.): ")
    detaylar = input("Proje hakkında daha fazla bilgi: ")

    # Proje oluştur ve çalıştır
    if proje_tur == "web sitesi":
        # Web sitesi kodunu oluştur ve tarayıcıda aç (örnek HTML/CSS/JS)
        ...
    elif proje_tur == "uygulama":
        ...
    # Diğer türler için benzer yapı
    ...
    print("Proje başarıyla oluşturuldu ve çalıştırıldı!")