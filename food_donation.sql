-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: dcds_project
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `collection_records`
--

DROP TABLE IF EXISTS `collection_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `collection_records` (
  `collection_id` int NOT NULL AUTO_INCREMENT,
  `donation_id` int NOT NULL,
  `collected_at` datetime DEFAULT NULL,
  `delivered_at` datetime DEFAULT NULL,
  `quantity_collected` decimal(10,2) DEFAULT NULL,
  `quantity_rejected` decimal(10,2) DEFAULT '0.00',
  `condition_on_arrival` enum('Good','Acceptable','Poor') DEFAULT 'Good',
  `receiver_signature_photo` varchar(255) DEFAULT NULL,
  `remarks` text,
  PRIMARY KEY (`collection_id`),
  UNIQUE KEY `donation_id` (`donation_id`),
  CONSTRAINT `fk_coll_donation` FOREIGN KEY (`donation_id`) REFERENCES `donations` (`donation_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `collection_records`
--

LOCK TABLES `collection_records` WRITE;
/*!40000 ALTER TABLE `collection_records` DISABLE KEYS */;
INSERT INTO `collection_records` VALUES (1,1,'2026-09-28 22:05:00','2026-09-28 22:40:00',40.00,0.00,'Good','signatures/don_001.jpg','Delivered hot and fresh'),(2,2,'2026-09-28 20:50:00','2026-09-28 21:20:00',15.00,1.00,'Acceptable','signatures/don_002.jpg','1 kg slightly stale, discarded'),(3,3,'2026-09-29 22:35:00','2026-09-29 23:15:00',60.00,0.00,'Good','signatures/don_003.jpg',NULL),(4,4,'2026-09-30 18:05:00','2026-09-30 18:50:00',25.00,2.50,'Acceptable','signatures/don_004.jpg','Some leafy items wilted'),(5,5,'2026-10-01 19:05:00','2026-10-01 19:40:00',60.00,0.00,'Good','signatures/don_005.jpg',NULL),(6,6,'2026-10-01 19:35:00','2026-10-01 20:10:00',40.00,0.00,'Good','signatures/don_006.jpg','Distributed to children'),(7,7,'2026-10-04 07:35:00',NULL,12.00,0.00,'Good',NULL,'Currently on the way'),(8,8,'2026-10-03 23:05:00','2026-10-03 23:30:00',30.00,5.00,'Poor','signatures/don_008.jpg','5 plates rejected, rice had cooled too long');
/*!40000 ALTER TABLE `collection_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `donation_requests`
--

DROP TABLE IF EXISTS `donation_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donation_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `surplus_id` int NOT NULL,
  `receiver_id` int NOT NULL,
  `requested_quantity` decimal(10,2) NOT NULL,
  `request_status` enum('Pending','Approved','Rejected') DEFAULT 'Pending',
  `requested_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`request_id`),
  UNIQUE KEY `uq_request` (`surplus_id`,`receiver_id`),
  KEY `fk_req_receiver` (`receiver_id`),
  CONSTRAINT `fk_req_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `receivers` (`receiver_id`),
  CONSTRAINT `fk_req_surplus` FOREIGN KEY (`surplus_id`) REFERENCES `surplus_food` (`surplus_id`) ON DELETE CASCADE,
  CONSTRAINT `donation_requests_chk_1` CHECK ((`requested_quantity` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `donation_requests`
--

LOCK TABLES `donation_requests` WRITE;
/*!40000 ALTER TABLE `donation_requests` DISABLE KEYS */;
INSERT INTO `donation_requests` VALUES (1,1,1,40.00,'Approved','2026-09-28 16:15:00'),(2,2,2,15.00,'Approved','2026-09-28 14:45:00'),(3,3,3,60.00,'Approved','2026-09-29 16:40:00'),(4,4,4,25.00,'Approved','2026-09-30 11:50:00'),(5,5,5,60.00,'Approved','2026-10-01 12:40:00'),(6,5,6,40.00,'Approved','2026-10-01 12:55:00'),(7,6,7,12.00,'Approved','2026-10-03 14:40:00'),(8,8,8,10.00,'Rejected','2026-10-01 07:30:00');
/*!40000 ALTER TABLE `donation_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `donations`
--

DROP TABLE IF EXISTS `donations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donations` (
  `donation_id` int NOT NULL AUTO_INCREMENT,
  `surplus_id` int NOT NULL,
  `receiver_id` int NOT NULL,
  `volunteer_id` int DEFAULT NULL,
  `quantity_donated` decimal(10,2) NOT NULL,
  `scheduled_pickup_time` datetime DEFAULT NULL,
  `donation_status` enum('Scheduled','In Transit','Completed','Cancelled') DEFAULT 'Scheduled',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`donation_id`),
  KEY `fk_don_surplus` (`surplus_id`),
  KEY `fk_don_receiver` (`receiver_id`),
  KEY `fk_don_volunteer` (`volunteer_id`),
  KEY `idx_don_status` (`donation_status`),
  CONSTRAINT `fk_don_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `receivers` (`receiver_id`),
  CONSTRAINT `fk_don_surplus` FOREIGN KEY (`surplus_id`) REFERENCES `surplus_food` (`surplus_id`),
  CONSTRAINT `fk_don_volunteer` FOREIGN KEY (`volunteer_id`) REFERENCES `volunteers` (`volunteer_id`) ON DELETE SET NULL,
  CONSTRAINT `donations_chk_1` CHECK ((`quantity_donated` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `donations`
--

LOCK TABLES `donations` WRITE;
/*!40000 ALTER TABLE `donations` DISABLE KEYS */;
INSERT INTO `donations` VALUES (1,1,1,1,40.00,'2026-09-28 22:00:00','Completed','2026-09-28 16:20:00'),(2,2,2,2,15.00,'2026-09-28 20:45:00','Completed','2026-09-28 14:50:00'),(3,3,3,3,60.00,'2026-09-29 22:30:00','Completed','2026-09-29 16:45:00'),(4,4,4,4,25.00,'2026-09-30 18:00:00','Completed','2026-09-30 12:00:00'),(5,5,5,5,60.00,'2026-10-01 19:00:00','Completed','2026-10-01 12:45:00'),(6,5,6,6,40.00,'2026-10-01 19:30:00','Completed','2026-10-01 13:00:00'),(7,6,7,7,12.00,'2026-10-04 07:30:00','In Transit','2026-10-03 14:45:00'),(8,7,8,NULL,30.00,'2026-10-03 23:00:00','Completed','2026-10-03 17:10:00');
/*!40000 ALTER TABLE `donations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `donors`
--

DROP TABLE IF EXISTS `donors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donors` (
  `donor_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `organization_name` varchar(150) NOT NULL,
  `donor_type` enum('Restaurant','Canteen','Event','Hotel') NOT NULL,
  `address` varchar(255) NOT NULL,
  `city` varchar(80) NOT NULL,
  `latitude` decimal(9,6) DEFAULT NULL,
  `longitude` decimal(9,6) DEFAULT NULL,
  `license_no` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`donor_id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `fk_donor_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `donors`
--

LOCK TABLES `donors` WRITE;
/*!40000 ALTER TABLE `donors` DISABLE KEYS */;
INSERT INTO `donors` VALUES (1,1,'Spice Garden Restaurant','Restaurant','12 FC Road, Shivajinagar','Pune',18.520430,73.856743,'FSSAI-PN-10001'),(2,2,'Sunrise Bakery','Restaurant','45 MG Road, Camp','Pune',18.514800,73.877600,'FSSAI-PN-10002'),(3,3,'Grand Palace Hotel','Hotel','7 Bund Garden Road','Pune',18.534100,73.881300,'FSSAI-PN-10003'),(4,4,'TechPark Canteen','Canteen','Block C, Hinjewadi Phase 1','Pune',18.591000,73.738900,'FSSAI-PN-10004'),(5,5,'Royal Events & Caterers','Event','22 Baner Road','Pune',18.559000,73.779100,'FSSAI-PN-10005'),(6,6,'Sweet Corner','Restaurant','3 Laxmi Road, Budhwar Peth','Pune',18.513200,73.853600,'FSSAI-PN-10006'),(7,7,'Lakeview Hotel','Hotel','88 Koregaon Park','Pune',18.536200,73.894000,'FSSAI-PN-10007'),(8,8,'Greenleaf Dairy Cafe','Canteen','19 Kothrud Main Road','Pune',18.507400,73.807700,'FSSAI-PN-10008');
/*!40000 ALTER TABLE `donors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `food_categories`
--

DROP TABLE IF EXISTS `food_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `food_categories` (
  `category_id` int NOT NULL AUTO_INCREMENT,
  `category_name` varchar(60) NOT NULL,
  `storage_type` enum('Hot','Cold','Ambient') NOT NULL,
  `default_shelf_life_hours` int NOT NULL,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `category_name` (`category_name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `food_categories`
--

LOCK TABLES `food_categories` WRITE;
/*!40000 ALTER TABLE `food_categories` DISABLE KEYS */;
INSERT INTO `food_categories` VALUES (1,'Cooked Meals','Hot',6),(2,'Bakery Items','Ambient',48),(3,'Dairy Products','Cold',72),(4,'Fruits & Vegetables','Ambient',96),(5,'Packaged Food','Ambient',720),(6,'Beverages','Cold',48),(7,'Rice & Grains (Cooked)','Hot',6),(8,'Sweets & Desserts','Ambient',24);
/*!40000 ALTER TABLE `food_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `impact_metrics`
--

DROP TABLE IF EXISTS `impact_metrics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `impact_metrics` (
  `metric_id` int NOT NULL AUTO_INCREMENT,
  `donor_id` int NOT NULL,
  `month_year` date NOT NULL,
  `total_generated` decimal(12,2) DEFAULT '0.00',
  `total_donated` decimal(12,2) DEFAULT '0.00',
  `total_wasted` decimal(12,2) DEFAULT '0.00',
  `recovery_rate` decimal(5,2) DEFAULT '0.00',
  `meals_served` int DEFAULT '0',
  `co2_saved_kg` decimal(12,2) DEFAULT '0.00',
  PRIMARY KEY (`metric_id`),
  UNIQUE KEY `uq_donor_month` (`donor_id`,`month_year`),
  CONSTRAINT `fk_metric_donor` FOREIGN KEY (`donor_id`) REFERENCES `donors` (`donor_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `impact_metrics`
--

LOCK TABLES `impact_metrics` WRITE;
/*!40000 ALTER TABLE `impact_metrics` DISABLE KEYS */;
INSERT INTO `impact_metrics` VALUES (1,1,'2026-09-01',200.00,150.00,50.00,75.00,375,375.00),(2,2,'2026-09-01',120.00,90.00,30.00,75.00,225,225.00),(3,3,'2026-09-01',400.00,260.00,140.00,65.00,650,650.00),(4,4,'2026-09-01',150.00,120.00,30.00,80.00,300,300.00),(5,5,'2026-09-01',500.00,350.00,150.00,70.00,875,875.00),(6,6,'2026-09-01',80.00,60.00,20.00,75.00,150,150.00),(7,7,'2026-09-01',250.00,150.00,100.00,60.00,375,375.00),(8,8,'2026-09-01',60.00,24.00,36.00,40.00,60,60.00);
/*!40000 ALTER TABLE `impact_metrics` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `receivers`
--

DROP TABLE IF EXISTS `receivers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `receivers` (
  `receiver_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `organization_name` varchar(150) NOT NULL,
  `receiver_type` enum('NGO','Shelter','Community Kitchen','Orphanage','Individual') NOT NULL,
  `address` varchar(255) NOT NULL,
  `city` varchar(80) NOT NULL,
  `capacity_per_day` int DEFAULT '0',
  `is_verified` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`receiver_id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `fk_receiver_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `receivers`
--

LOCK TABLES `receivers` WRITE;
/*!40000 ALTER TABLE `receivers` DISABLE KEYS */;
INSERT INTO `receivers` VALUES (1,9,'Annadaan Trust','NGO','5 Sadashiv Peth','Pune',200,1),(2,10,'Asharayam Shelter','Shelter','14 Hadapsar Gaon','Pune',120,1),(3,11,'Seva Community Kitchen','Community Kitchen','31 Kondhwa Road','Pune',300,1),(4,12,'Nanhi Duniya Orphanage','Orphanage','9 Wanowrie','Pune',80,1),(5,13,'Hope Foundation','NGO','27 Aundh Road','Pune',150,1),(6,14,'Bhojan Seva Kitchen','Community Kitchen','60 Pimpri Colony','Pune',250,0),(7,15,'Night Shelter Pune','Shelter','2 Swargate','Pune',100,1),(8,16,'Sunita Pawar','Individual','18 Yerwada','Pune',20,0);
/*!40000 ALTER TABLE `receivers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `surplus_food`
--

DROP TABLE IF EXISTS `surplus_food`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `surplus_food` (
  `surplus_id` int NOT NULL AUTO_INCREMENT,
  `donor_id` int NOT NULL,
  `category_id` int NOT NULL,
  `food_name` varchar(120) NOT NULL,
  `quantity` decimal(10,2) NOT NULL,
  `unit` enum('kg','plates','packets') NOT NULL,
  `prepared_at` datetime DEFAULT NULL,
  `expiry_datetime` datetime NOT NULL,
  `pickup_address` varchar(255) NOT NULL,
  `status` enum('Available','Reserved','Collected','Expired','Wasted') DEFAULT 'Available',
  `listed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `notes` text,
  PRIMARY KEY (`surplus_id`),
  KEY `fk_surplus_category` (`category_id`),
  KEY `fk_surplus_unit` (`unit`),
  KEY `idx_surplus_status_expiry` (`status`,`expiry_datetime`),
  KEY `idx_surplus_donor` (`donor_id`),
  CONSTRAINT `fk_surplus_category` FOREIGN KEY (`category_id`) REFERENCES `food_categories` (`category_id`),
  CONSTRAINT `fk_surplus_donor` FOREIGN KEY (`donor_id`) REFERENCES `donors` (`donor_id`),
  CONSTRAINT `fk_surplus_unit` FOREIGN KEY (`unit`) REFERENCES `unit_conversions` (`unit`),
  CONSTRAINT `surplus_food_chk_1` CHECK ((`quantity` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `surplus_food`
--

LOCK TABLES `surplus_food` WRITE;
/*!40000 ALTER TABLE `surplus_food` DISABLE KEYS */;
INSERT INTO `surplus_food` VALUES (1,1,1,'Vegetable Biryani',40.00,'plates','2026-09-28 19:00:00','2026-09-29 01:00:00','12 FC Road, Shivajinagar','Collected','2026-09-28 16:00:00','Leftover from dinner service'),(2,2,2,'Assorted Bread Loaves',15.00,'kg','2026-09-28 06:00:00','2026-09-30 06:00:00','45 MG Road, Camp','Collected','2026-09-28 14:30:00','Unsold end-of-day bread'),(3,3,1,'Dal Tadka with Roti',60.00,'plates','2026-09-29 18:30:00','2026-09-30 00:30:00','7 Bund Garden Road','Collected','2026-09-29 16:30:00','Wedding buffet surplus'),(4,4,4,'Fresh Seasonal Vegetables',25.00,'kg','2026-09-30 08:00:00','2026-10-04 08:00:00','Block C, Hinjewadi Phase 1','Collected','2026-09-30 11:30:00','Excess from canteen stock'),(5,5,5,'Packed Snack Boxes',100.00,'packets','2026-10-01 10:00:00','2026-10-31 10:00:00','22 Baner Road','Collected','2026-10-01 12:30:00','Conference event leftovers'),(6,6,8,'Mixed Indian Sweets',12.00,'kg','2026-10-03 09:00:00','2026-10-04 09:00:00','3 Laxmi Road, Budhwar Peth','Reserved','2026-10-03 14:30:00','Festival season overstock'),(7,7,7,'Jeera Rice',30.00,'plates','2026-10-03 19:00:00','2026-10-04 01:00:00','88 Koregaon Park','Collected','2026-10-03 17:00:00',NULL),(8,8,3,'Paneer and Curd Tubs',10.00,'kg','2026-10-01 08:00:00','2026-10-04 08:00:00','19 Kothrud Main Road','Wasted','2026-10-01 06:30:00','No pickup arranged before expiry');
/*!40000 ALTER TABLE `surplus_food` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `unit_conversions`
--

DROP TABLE IF EXISTS `unit_conversions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unit_conversions` (
  `unit` enum('kg','plates','packets') NOT NULL,
  `kg_per_unit` decimal(6,3) NOT NULL,
  PRIMARY KEY (`unit`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unit_conversions`
--

LOCK TABLES `unit_conversions` WRITE;
/*!40000 ALTER TABLE `unit_conversions` DISABLE KEYS */;
INSERT INTO `unit_conversions` VALUES ('kg',1.000),('plates',0.400),('packets',0.250);
/*!40000 ALTER TABLE `unit_conversions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(150) NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('Admin','Donor','Receiver','Volunteer') NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Rajesh Kulkarni','rajesh@spicegarden.com','9822001101','$2y$10$dummyhash0000000000000001','Donor','2026-10-05 12:35:42'),(2,'Anita Deshmukh','anita@sunrisebakery.com','9822001102','$2y$10$dummyhash0000000000000002','Donor','2026-10-05 12:35:42'),(3,'Vikram Malhotra','vikram@grandpalace.com','9822001103','$2y$10$dummyhash0000000000000003','Donor','2026-10-05 12:35:42'),(4,'Sneha Joshi','sneha@techparkcanteen.com','9822001104','$2y$10$dummyhash0000000000000004','Donor','2026-10-05 12:35:42'),(5,'Imran Shaikh','imran@royalevents.com','9822001105','$2y$10$dummyhash0000000000000005','Donor','2026-10-05 12:35:42'),(6,'Priya Nair','priya@sweetcorner.com','9822001106','$2y$10$dummyhash0000000000000006','Donor','2026-10-05 12:35:42'),(7,'Arjun Patil','arjun@lakeviewhotel.com','9822001107','$2y$10$dummyhash0000000000000007','Donor','2026-10-05 12:35:42'),(8,'Meera Kapoor','meera@greenleafdairy.com','9822001108','$2y$10$dummyhash0000000000000008','Donor','2026-10-05 12:35:42'),(9,'Suresh Iyer','suresh@annadaan.org','9822002201','$2y$10$dummyhash0000000000000009','Receiver','2026-10-05 12:35:42'),(10,'Kavita Rao','kavita@asharayam.org','9822002202','$2y$10$dummyhash0000000000000010','Receiver','2026-10-05 12:35:42'),(11,'Mohan Das','mohan@sevakitchen.org','9822002203','$2y$10$dummyhash0000000000000011','Receiver','2026-10-05 12:35:42'),(12,'Fatima Sheikh','fatima@nanhidunia.org','9822002204','$2y$10$dummyhash0000000000000012','Receiver','2026-10-05 12:35:42'),(13,'Deepak Verma','deepak@hopefoundation.org','9822002205','$2y$10$dummyhash0000000000000013','Receiver','2026-10-05 12:35:42'),(14,'Lakshmi Menon','lakshmi@bhojanseva.org','9822002206','$2y$10$dummyhash0000000000000014','Receiver','2026-10-05 12:35:42'),(15,'Ramesh Gaikwad','ramesh@nightshelter.org','9822002207','$2y$10$dummyhash0000000000000015','Receiver','2026-10-05 12:35:42'),(16,'Sunita Pawar','sunita.pawar@gmail.com','9822002208','$2y$10$dummyhash0000000000000016','Receiver','2026-10-05 12:35:42'),(17,'Rohan Mehta','rohan.mehta@gmail.com','9822003301','$2y$10$dummyhash0000000000000017','Volunteer','2026-10-05 12:35:42'),(18,'Neha Singh','neha.singh@gmail.com','9822003302','$2y$10$dummyhash0000000000000018','Volunteer','2026-10-05 12:35:42'),(19,'Aditya Bhosale','aditya.b@gmail.com','9822003303','$2y$10$dummyhash0000000000000019','Volunteer','2026-10-05 12:35:42'),(20,'Pooja Chavan','pooja.c@gmail.com','9822003304','$2y$10$dummyhash0000000000000020','Volunteer','2026-10-05 12:35:42'),(21,'Karan Thakur','karan.t@gmail.com','9822003305','$2y$10$dummyhash0000000000000021','Volunteer','2026-10-05 12:35:42'),(22,'Ishita Bansal','ishita.b@gmail.com','9822003306','$2y$10$dummyhash0000000000000022','Volunteer','2026-10-05 12:35:42'),(23,'Sanjay More','sanjay.more@gmail.com','9822003307','$2y$10$dummyhash0000000000000023','Volunteer','2026-10-05 12:35:42'),(24,'Divya Kulkarni','divya.k@gmail.com','9822003308','$2y$10$dummyhash0000000000000024','Volunteer','2026-10-05 12:35:42');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `volunteers`
--

DROP TABLE IF EXISTS `volunteers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `volunteers` (
  `volunteer_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `vehicle_type` enum('None','Bike','Car','Van') DEFAULT 'None',
  `availability_status` enum('Available','Busy','Offline') DEFAULT 'Available',
  `area_served` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`volunteer_id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `fk_volunteer_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `volunteers`
--

LOCK TABLES `volunteers` WRITE;
/*!40000 ALTER TABLE `volunteers` DISABLE KEYS */;
INSERT INTO `volunteers` VALUES (1,17,'Bike','Available','Shivajinagar, Camp'),(2,18,'Car','Available','Koregaon Park, Hadapsar'),(3,19,'Van','Busy','Hinjewadi, Baner, Aundh'),(4,20,'Bike','Available','Kothrud, Karve Nagar'),(5,21,'Van','Available','Pune City, Swargate'),(6,22,'None','Offline','Wakad, Pimpri'),(7,23,'Car','Busy','Kondhwa, Wanowrie'),(8,24,'Bike','Available','Yerwada, Viman Nagar');
/*!40000 ALTER TABLE `volunteers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `waste_records`
--

DROP TABLE IF EXISTS `waste_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `waste_records` (
  `waste_id` int NOT NULL AUTO_INCREMENT,
  `donor_id` int NOT NULL,
  `surplus_id` int DEFAULT NULL,
  `category_id` int NOT NULL,
  `quantity_wasted` decimal(10,2) NOT NULL,
  `unit` enum('kg','plates','packets') NOT NULL,
  `waste_reason` enum('Expired','Overproduction','Spoiled','Plate Waste','Unsold') NOT NULL,
  `recorded_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `estimated_cost` decimal(10,2) DEFAULT '0.00',
  PRIMARY KEY (`waste_id`),
  KEY `fk_waste_donor` (`donor_id`),
  KEY `fk_waste_surplus` (`surplus_id`),
  KEY `fk_waste_category` (`category_id`),
  KEY `fk_waste_unit` (`unit`),
  KEY `idx_waste_reason` (`waste_reason`),
  KEY `idx_waste_date` (`recorded_at`),
  CONSTRAINT `fk_waste_category` FOREIGN KEY (`category_id`) REFERENCES `food_categories` (`category_id`),
  CONSTRAINT `fk_waste_donor` FOREIGN KEY (`donor_id`) REFERENCES `donors` (`donor_id`),
  CONSTRAINT `fk_waste_surplus` FOREIGN KEY (`surplus_id`) REFERENCES `surplus_food` (`surplus_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_waste_unit` FOREIGN KEY (`unit`) REFERENCES `unit_conversions` (`unit`),
  CONSTRAINT `waste_records_chk_1` CHECK ((`quantity_wasted` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `waste_records`
--

LOCK TABLES `waste_records` WRITE;
/*!40000 ALTER TABLE `waste_records` DISABLE KEYS */;
INSERT INTO `waste_records` VALUES (1,8,8,3,10.00,'kg','Expired','2026-10-04 03:30:00',1500.00),(2,1,NULL,1,15.00,'plates','Plate Waste','2026-09-28 17:30:00',900.00),(3,2,NULL,2,8.00,'kg','Unsold','2026-09-29 15:30:00',640.00),(4,3,NULL,1,20.00,'plates','Overproduction','2026-09-29 19:00:00',2400.00),(5,4,NULL,4,12.00,'kg','Spoiled','2026-10-02 04:30:00',480.00),(6,5,NULL,5,30.00,'packets','Overproduction','2026-10-02 06:30:00',1050.00),(7,6,NULL,8,3.50,'kg','Unsold','2026-10-04 15:30:00',875.00),(8,7,NULL,7,10.00,'plates','Plate Waste','2026-10-03 18:45:00',500.00);
/*!40000 ALTER TABLE `waste_records` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-06  9:29:47
