import { By, until } from 'selenium-webdriver';
import { driver, test } from 'thousandeyes';

runScript();

async function runScript() {
  const settings = test.getSettings();
  await driver.manage().setTimeouts({
    implicit: Math.floor((settings.timeout || 60) * 500),
    pageLoad: 60000
  });

  await driver.get('__FRONTEND_URL__/admin/login');

  await driver.findElement(By.id('email')).clear();
  await driver.findElement(By.id('email')).sendKeys('__ADMIN_EMAIL__');
  await driver.findElement(By.id('password')).clear();
  await driver.findElement(By.id('password')).sendKeys('__ADMIN_PASSWORD__');
  await driver.findElement(By.css('button[type="submit"]')).click();

  await driver.wait(until.urlMatches(/\/admin(\/)?$/), 30000);
  await driver.findElement(By.css('a[href="/admin/orders/import"]'));

  await driver.get('__FRONTEND_URL__/admin/orders/import');
  await driver.wait(until.urlContains('/admin/orders/import'), 10000);
  await driver.findElement(By.xpath("//h1[contains(., 'Import Orders')]"));
}
