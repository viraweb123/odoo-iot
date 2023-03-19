# iot-box
connect office devices into the ERP system

## سه تاپیک در broker داریم(attendence _ employees _ maintenance) 
<br />
تاپیک attendence : 
<br />
این تاپیک برای ثبت حضور و غیاب ها است. داده های حضور و غیاب از دستگاه zk را در odoo ثبت میکند
ساختار داده ای که از zk به تاپیک attedence وارد میشود. 
<br /><br />

<pre>
thing_id = int (zk id)
attendence[{  
  employee_id = int  
  timestamp = datetime  
  punch = int [1,4] 1:in 4:out  
}, ]  
</pre>
داده هایی که از تاپیک attendence  در odoo ثبت میشود. این داده ها صرفا در یک جدول به جز جدول hr_attendence در odoo ثبت میشود.  ای داده های پس از چک شدن در جدول اصلی ذخیره میشود  <br />


تاپیک employee: این تاپیک برای ثبت نام کاربران است.  <br />
ساختار داده هایی که از دستگاه zk وارد تاپیک employee و از تاپیک employee وارد odoo میشود. <br />

<pre>
things_id = int 
employee{[ 
  employee_id = int 
  employee_name = str 
  password = (number or finger print) 
]} 
</pre>

ساختار داده هایی که از odoo وارد تاپیک employee و از تاپیک employee وارد zk میشود. <br /> مشابه ساختار بالا است <br /> 

تاپیک maintenance: اگر دستگاه جدیدی وارد سیستم شود یا دستگاهی خراب شود از این تاپیک استفاده میشود <br />
مثلا اگر دستگاه جدیدی وصل شود<br /> 
<pre>
things_id = int 
devices [{
}]
</pre>

اگر این اتفاق بیفته . odoo باید لیست کاربران را در تاپیک employee قرار بده و دستگاه zk جدید لیست کاربران را بخواند. 
