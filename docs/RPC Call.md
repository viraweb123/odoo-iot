

# چه کسی بخواند؟

در این سند پروتکل rpc به صورت فنی بیان شده و برای توسعه دهندگان مناسب است
.
# RPC



در RPC از سمت odoo (گیرنده) در خواست میاد و gateway thingsboard ( سرور ) به این درخواست پاسخ میده. 

هر در خواست باعث میشه تابع server_side_rpc_handler از یک connector صدازده بشه. اینکه کدوم connector باشه بستگی داره تو درخواست rpc از id کدوم گیرنده استفاده بشه.

هدف اینه هر درخواستی که از سمت odoo میاد یک متد با پارامترهاش را ارسال کنه. مطابق اون متد و پارامترها در gateway درخواست انجام میشه.

# Attendence

اگر فرض کنیم دستگاه موردنظر یک دستگاه حضور و غیاب باشد. ما نیاز داریم به درخواست:

### 1- به روزرسانی همزمان چند کاربر  (متد update_user)

در این متد چک میشه. اگر کاربری با user_id ارسالی وجود داشت آن کاربر حذف میشه و کاربر جدیدی با داده های ارسالی ساخته میشه

اگر کاربری با user_id ارسالی وجود نداشت آن کاربر ساخته میشه


درخواست باید شامل نام متد update_user و پارامترهای موردنیاز آن باشد.


پارامترهای موردنیاز متد update_user : 



uid : کاربر uid  (int, required, )

name : نام کاربر (str)

privilege : امتیاز کاربر  (str)

password : رمز کاربر (str)

group_id : گروه id (str) 

user_id : کاربر id (str)

card : card (int, required, )

*نکته : ما فرض میکنیم uid همیشه با user_id برابر است. 



### نمونه ای از درخواست ارسالی


```json
{
  "method": "update_user",
  "params": {
  
      "0" : {
      "uid": "33",
      "name": "zahra",
      "privilege":"",
      "password" : "",
      "group_id" : "",
      "user_id" : "33",
      "card" : "0"
      },

      "1" : {
      "uid": "38",
      "name": "fateme",
      "privilege":"",
      "password" : "",
      "group_id" : "",
      "user_id" : "38",
      "card" : "0"
      }
  }
}
```

### نمونه ای از متد update_user

```python
def update_user(self, params , content):
    if not self.connection:
        raise Exception("Device is not connected")
    users = self.connection.get_users()

    for key, value in params.items():
        # Check user is exist        
        exist_user = 0
        for item in users:
            if item.user_id == value["user_id"]:
                exist_user = item


        # user not exist Create user 
        if exist_user == 0:
            self.connection.set_user(int(value["uid"]),
                        value["name"],
                        value["privilege"],
                        value["password"],
                        value["group_id"],
                        value["user_id"],
                        int(value["card"])
                        )
        else:
            # user is exist delete and create
            # save finger print

            fingers = self.connection.get_templates()

            save_fingers = []
            for finger in fingers:
                if finger.uid == value["uid"]:
                    save_fingers.append(finger)


            self.connection.delete_user(user_id=value["user_id"])

            self.connection.set_user(int(value["uid"]),
                        value["name"],
                        value["privilege"],
                        value["password"],
                        value["group_id"],
                        value["user_id"],
                        int(value["card"])
                        )
            # add finger print
            self.connection.save_user_template(value["uid"], save_fingers) 

        self.gateway.send_rpc_reply(
                        device= content["device"], 
                        req_id= content["data"]["id"],
                        content = {"success_sent": 'True'}
                    )
```

### 2- حذف کاربر (متد del_user)

یعنی به ازای هر کاربری که در odoo حذف میشه باید اون کاربر در دستگاه هم حذف بشه.

درخواست باید شامل نام متد del_user و پارامترهای موردنیاز آن باشد.

پارامترهای موردنیاز del_user :
user_id : کاربری که حذف شده user_id

### نمونه ای از درخواست ارسالی


نمونه ای از درخواست ارسالی برای حذف چند کاربر

```json
{
  "method": "del_user",
  "params": {
    
      "0" : {"user_id_delete" : "109"},
      "1" : {"user_id_delete" : "110"}
  }
}

```

### نمونه ای از متد del_user

```python
def del_user(self , params , content):
    if not self.connection:
        raise Exception("Device is not connected")

    for key, value in params.items():              

        self.connection.delete_user(user_id=value['user_id_delete'])

        self.gateway.send_rpc_reply(
        device= content["device"], 
        req_id= content["data"]["id"],
        content = {"success_sent": 'True'}
        )
```




### 4- ذخیره اثرانگشت ( متد save_fingerprint )

مثلا از طرف odoo درخواست ذخیره اثر انگشت یک کاربر مشخص وارد میشه.

درخواست باید شامل متد save_fingerprint و پارامترهای موردنیاز آن باشد.

پارامترهای مورد نیاز متدupdate_fingerprint  :


uid_change : کاربری که قرار هست اثر انگشتش ذخیره بشه uid

*نکته : متد ذخیره اثرانگشت با uid کار میکنه


### نمونه ای از درخواست ارسالی


```json
{
  "method": "update_fingerprint",
  "params": {
    "user_id_change" : "199"
  }
}

```

### نمونه ای از متد update_fingerprint


```python
def update_fingerprint(self, params):
        if not self.connection:
            raise Exception("Device is not connected")
     
        self.connection.enroll_user(int(params["user_id_change"]))
        
        #template = self.connection.get_user_template(uid=int(params["user_id_change"]), temp_id=0)
        

```



# Printer

### 1-پرینت کردن فایل ( متد print_file)

از odoo یک درخواست پرینت به دستگاه ارسال میشه. 

درخواست باید شامل نام متد print_file و پارامترهای مورد نیاز متد باشه

پارامترهای مورد نیاز متد print_file : 


 content : دریافت میشه base64 محتوایی که قرار هست پرسینت بشه که به صورت
 
 suffix_file_name : با اون پسوند در سیستمی که پرینتر بهش وصل هست ذخیره میشه contetn  پسوند فایلی هست که 


### نمونه ای از درخواست ارسالی
```json
{
  "method": "print_file",

  "params": {
    "content" :  base 64 image,
    "suffix_file_name": ".jpg"
  }
}
```

### نمونه ای از متد print_file

```python
def print_file(self, printer_name , printer_file): 
        printid = self.connection.printFile(printer_name, printer_file ,'' , {})
```
