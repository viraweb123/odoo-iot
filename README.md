# iot-box
connect office devices into the ERP system

سه تاپیک در broker داریم . attendence _ employees _ maintenance 
<br />
تاپیک attendence : 
این تاپیک برای ثبت حضور و غیاب ها است. داده های حضور و غیاب از دستگاه zk را در odoo ثبت میکند
ساختار داده ای که از zk به تاپیک attedence وارد میشود. 
thing_id = int (zk id)
attendence[{
  employee_id = int
  timestamp = datetime
  punch = int [1,4] 1:in 4:out
}, ]

داده هایی که از تاپیک attendence  در odoo ثبت میشود. این داده ها صرفا در یک جدول به جز جدول hr_attendence در odoo ثبت میشود.  ای داده های پس از چک شدن در جدول اصلی ذخیره میشود.


تاپیک employee: این تاپیک برای ثبت نام کاربران است. 
ساختار داده هایی که از دستگاه zk وارد تاپیک employee و از تاپیک employee وارد odoo میشود.


things_id = int
employee{[
  employee_id = int
  employee_name = str
  password = (number or finger print)
]}

ساختار داده هایی که از odoo وارد تاپیک employee و از تاپیک employee وارد zk میشود.
things_id = int
employee{[
  employee_id = int
  employee_name = str
  password = (number or finger print)
]}



تاپیک maintenance: اگر دستگاه جدیدی وارد سیستم شود یا دستگاهی خراب شود از این تاپیک استفاده میشود
مثلا اگر دستگاه جدیدی وصل شود
things_id = int
devices[{
  problem : syc
}]

اگر این اتفاق بیفته . odoo باید لیست کاربران را در تاپیک employee قرار بده و دستگاه zk جدید لیست کاربران را بخواند. 
