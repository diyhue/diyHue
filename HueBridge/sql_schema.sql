-- phpMyAdmin SQL Dump
-- version 4.6.5.2
-- https://www.phpmyadmin.net/
--
-- Host: 192.168.10.111
-- Generation Time: 24 Mar 2017 la 22:02
-- Versiune server: 10.0.28-MariaDB-0ubuntu0.16.04.1
-- PHP Version: 7.0.13-0ubuntu0.16.04.1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `hue`
--
CREATE DATABASE IF NOT EXISTS `hue` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT USAGE ON hue.* TO 'hue'@'localhost' IDENTIFIED BY 'hue123';
GRANT ALL PRIVILEGES ON hue.* TO 'hue'@'localhost';
FLUSH PRIVILEGES;
USE `hue`;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `groups`
--

DROP TABLE IF EXISTS `groups`;
CREATE TABLE `groups` (
  `id` int(11) NOT NULL,
  `lights` varchar(50) NOT NULL,
  `name` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `class` varchar(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `lights`
--

DROP TABLE IF EXISTS `lights`;
CREATE TABLE `lights` (
  `id` smallint(11) NOT NULL,
  `state` tinyint(1) NOT NULL DEFAULT '0',
  `bri` smallint(6) NOT NULL,
  `hue` smallint(6) NOT NULL,
  `sat` smallint(6) NOT NULL,
  `xy` varchar(20) NOT NULL,
  `ct` smallint(6) NOT NULL,
  `alert` varchar(10) NOT NULL DEFAULT 'None',
  `effect` varchar(10) NOT NULL DEFAULT 'None',
  `colormode` varchar(10) NOT NULL,
  `type` varchar(50) NOT NULL,
  `name` varchar(30) NOT NULL,
  `uniqueid` varchar(30) NOT NULL,
  `modelid` varchar(10) NOT NULL,
  `swversion` varchar(8) NOT NULL,
  `ip` varchar(20) NOT NULL,
  `strip_light_nr` tinyint(4) NOT NULL DEFAULT '1',
  `new` tinyint(1) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `lightstates`
--

DROP TABLE IF EXISTS `lightstates`;
CREATE TABLE `lightstates` (
  `id` smallint(6) NOT NULL,
  `light_id` smallint(6) NOT NULL,
  `scene_id` smallint(6) NOT NULL,
  `state` tinyint(1) NOT NULL,
  `bri` smallint(4) NOT NULL,
  `xy` varchar(20) NOT NULL,
  `ct` smallint(4) NOT NULL,
  `transitiontime` mediumint(9) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `resourcelinks`
--

DROP TABLE IF EXISTS `resourcelinks`;
CREATE TABLE `resourcelinks` (
  `id` smallint(6) NOT NULL,
  `name` varchar(32) NOT NULL,
  `description` varchar(64) NOT NULL,
  `classid` mediumint(9) NOT NULL,
  `owner` varchar(40) NOT NULL,
  `recycle` tinyint(1) NOT NULL,
  `links` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `rules`
--

DROP TABLE IF EXISTS `rules`;
CREATE TABLE `rules` (
  `id` smallint(6) NOT NULL,
  `name` varchar(32) NOT NULL,
  `owner` varchar(40) NOT NULL,
  `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `lasttriggered` datetime NOT NULL,
  `timestriggered` smallint(6) NOT NULL DEFAULT '0',
  `status` varchar(10) NOT NULL DEFAULT 'enabled',
  `recycle` tinyint(1) NOT NULL,
  `conditions` text NOT NULL,
  `actions` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `scenes`
--

DROP TABLE IF EXISTS `scenes`;
CREATE TABLE `scenes` (
  `id` smallint(11) NOT NULL,
  `name` varchar(32) NOT NULL,
  `owner` varchar(40) NOT NULL,
  `lights` varchar(50) NOT NULL,
  `picture` varchar(16) NOT NULL,
  `lastupdated` datetime NOT NULL,
  `recycle` tinyint(1) NOT NULL,
  `appdata` varchar(100) NOT NULL,
  `locked` tinyint(1) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `schedules`
--

DROP TABLE IF EXISTS `schedules`;
CREATE TABLE `schedules` (
  `id` int(11) NOT NULL,
  `name` varchar(50) NOT NULL,
  `description` varchar(255) NOT NULL,
  `command` text NOT NULL,
  `local_time` varchar(30) NOT NULL,
  `created` datetime NOT NULL,
  `autodelete` tinyint(1) NOT NULL,
  `starttime` datetime NOT NULL,
  `status` varchar(10) NOT NULL,
  `recycle` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `sensors`
--

DROP TABLE IF EXISTS `sensors`;
CREATE TABLE `sensors` (
  `id` mediumint(11) NOT NULL,
  `type` varchar(32) NOT NULL,
  `state` varchar(255) NOT NULL,
  `config` text NOT NULL,
  `name` varchar(32) NOT NULL,
  `modelid` varchar(32) NOT NULL,
  `manufacturername` varchar(32) NOT NULL,
  `uniqueid` varchar(32) NOT NULL,
  `swversion` varchar(16) NOT NULL,
  `recycle` tinyint(1) NOT NULL DEFAULT '0',
  `new` tinyint(1) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Structura de tabel pentru tabelul `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` tinyint(3) NOT NULL,
  `username` varchar(40) NOT NULL,
  `devicetype` varchar(60) NOT NULL,
  `last_use_date` datetime NOT NULL,
  `create_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `groups`
--
ALTER TABLE `groups`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`);

--
-- Indexes for table `lights`
--
ALTER TABLE `lights`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `lightstates`
--
ALTER TABLE `lightstates`
  ADD PRIMARY KEY (`id`),
  ADD KEY `light_id` (`light_id`),
  ADD KEY `scene_id` (`scene_id`);

--
-- Indexes for table `resourcelinks`
--
ALTER TABLE `resourcelinks`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `rules`
--
ALTER TABLE `rules`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `scenes`
--
ALTER TABLE `scenes`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `schedules`
--
ALTER TABLE `schedules`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `sensors`
--
ALTER TABLE `sensors`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`),
  ADD KEY `username` (`username`),
  ADD KEY `id_2` (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `groups`
--
ALTER TABLE `groups`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `lights`
--
ALTER TABLE `lights`
  MODIFY `id` smallint(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `lightstates`
--
ALTER TABLE `lightstates`
  MODIFY `id` smallint(6) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `resourcelinks`
--
ALTER TABLE `resourcelinks`
  MODIFY `id` smallint(6) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `rules`
--
ALTER TABLE `rules`
  MODIFY `id` smallint(6) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `scenes`
--
ALTER TABLE `scenes`
  MODIFY `id` smallint(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `schedules`
--
ALTER TABLE `schedules`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `sensors`
--
ALTER TABLE `sensors`
  MODIFY `id` mediumint(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` tinyint(3) NOT NULL AUTO_INCREMENT;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
